import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from backend.api.resources import (
    UPLOAD_DIR,
    document_profile_store,
    ensure_upload_dir,
    is_supported_document,
    loader,
    milvus_manager,
    milvus_writer,
    parent_chunk_store,
    delete_document_transactionally,
    save_upload_file,
)
from backend.db.models import User
from backend.infra.auth import require_admin
from backend.jobs import DELETE_STEPS, delete_job_manager, upload_job_manager
from backend.schemas import (
    DocumentProfileBatchUpdateRequest,
    DocumentDeleteJobResponse,
    DocumentDeleteResponse,
    DocumentDeleteStartResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentProfileUpdateRequest,
    DocumentUploadJobResponse,
    DocumentUploadResponse,
    DocumentUploadStartResponse,
)

router = APIRouter(tags=["documents"])


def _normalize_profile_value(value: str | None) -> str:
    return str(value or "").strip()


def _build_profile_payload(
    *,
    filename: str,
    file_type: str,
    museum: str | None,
    exhibition: str | None,
    exhibit_id: str | None,
    era: str | None,
    category: str | None,
) -> dict:
    return {
        "filename": _normalize_profile_value(filename),
        "file_type": _normalize_profile_value(file_type),
        "museum": _normalize_profile_value(museum),
        "exhibition": _normalize_profile_value(exhibition),
        "exhibit_id": _normalize_profile_value(exhibit_id),
        "era": _normalize_profile_value(era),
        "category": _normalize_profile_value(category),
    }


def _quote_milvus_string(value: str) -> str:
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _get_document_stats(filename: str) -> dict | None:
    key = _normalize_profile_value(filename)
    if not key:
        return None
    rows = milvus_manager.query(
        filter_expr=f"filename == {_quote_milvus_string(key)}",
        output_fields=["filename", "file_type"],
        limit=10000,
    )
    if not rows:
        return None
    file_type = str(rows[0].get("file_type") or "").strip()
    return {
        "filename": key,
        "file_type": file_type,
        "chunk_count": len(rows),
    }


def _merge_document_profile(stats: dict) -> DocumentInfo:
    profile_map = document_profile_store.get_profile_map([stats["filename"]])
    profile = profile_map.get(stats["filename"], {})
    merged = dict(stats)
    merged.update(profile)
    return DocumentInfo(**merged)


def _dump_profile_fields(request: DocumentProfileUpdateRequest) -> dict:
    if hasattr(request, "model_dump"):
        return request.model_dump(exclude_unset=True)
    return request.dict(exclude_unset=True)


def _build_profile_patch_payload(
    *,
    filename: str,
    file_type: str,
    current_profile: dict | None,
    patch_data: dict,
) -> dict:
    current = current_profile or {}
    payload = {
        "filename": _normalize_profile_value(filename),
        "file_type": _normalize_profile_value(file_type),
        "museum": _normalize_profile_value(current.get("museum")),
        "exhibition": _normalize_profile_value(current.get("exhibition")),
        "exhibit_id": _normalize_profile_value(current.get("exhibit_id")),
        "era": _normalize_profile_value(current.get("era")),
        "category": _normalize_profile_value(current.get("category")),
    }
    for key in ("museum", "exhibition", "exhibit_id", "era", "category"):
        if key in patch_data:
            payload[key] = _normalize_profile_value(patch_data.get(key))
    return payload


def _process_upload_job(job_id: str, file_path: str, filename: str, profile_payload: dict | None = None) -> None:
    failed_step = "cleanup"
    try:
        upload_job_manager.complete_step(job_id, "upload", "文件已保存到服务器")

        failed_step = "cleanup"
        upload_job_manager.update_step(job_id, "cleanup", 10, "running", "正在清理同名旧文档")
        delete_document_transactionally(filename)
        upload_job_manager.complete_step(job_id, "cleanup", "旧版本清理完成")

        failed_step = "parse"
        upload_job_manager.update_step(job_id, "parse", 5, "running", "正在解析文档并执行三级分块")
        new_docs = loader.load_document(file_path, filename)
        if not new_docs:
            raise ValueError("文档处理失败，未能提取内容")

        parent_docs = [doc for doc in new_docs if int(doc.get("chunk_level", 0) or 0) in (1, 2)]
        leaf_docs = [doc for doc in new_docs if int(doc.get("chunk_level", 0) or 0) == 3]
        if not leaf_docs:
            raise ValueError("文档处理失败，未生成可检索叶子分块")
        upload_job_manager.complete_step(
            job_id,
            "parse",
            f"解析完成：父级分块 {len(parent_docs)} 个，叶子分块 {len(leaf_docs)} 个",
        )

        if profile_payload:
            failed_step = "parse"
            document_profile_store.upsert_profile(**profile_payload)

        failed_step = "parent_store"
        upload_job_manager.update_step(job_id, "parent_store", 20, "running", "正在写入父级分块")
        parent_chunk_store.upsert_documents(parent_docs)
        upload_job_manager.complete_step(job_id, "parent_store", f"父级分块已入库：{len(parent_docs)} 个")

        failed_step = "vector_store"
        total_leaf = len(leaf_docs)
        upload_job_manager.update_step(
            job_id,
            "vector_store",
            0,
            "running",
            f"正在向量化入库：0 / {total_leaf}",
            total_chunks=total_leaf,
            processed_chunks=0,
        )

        def _on_vector_progress(processed: int, total: int) -> None:
            percent = round(processed * 100 / total) if total else 100
            upload_job_manager.update_step(
                job_id,
                "vector_store",
                percent,
                "running",
                f"正在向量化入库：{processed} / {total}",
                total_chunks=total,
                processed_chunks=processed,
            )

        milvus_writer.write_documents(leaf_docs, progress_callback=_on_vector_progress)
        upload_job_manager.complete_step(job_id, "vector_store", f"向量化入库完成：{total_leaf} 个叶子分块")
        upload_job_manager.complete_job(job_id, f"成功上传并处理 {filename}")
    except Exception as e:
        upload_job_manager.fail_job(job_id, failed_step, str(e))


def _process_delete_job(job_id: str, filename: str) -> None:
    failed_step = "prepare"
    try:
        chunks_deleted = delete_document_transactionally(filename, delete_job_manager, job_id)
        delete_job_manager.complete_job(job_id, f"已删除 {filename}，向量数据 {chunks_deleted} 条")
    except Exception as e:
        job = delete_job_manager.get_job(job_id)
        current_step = job.get("current_step", "prepare") if job else "prepare"
        delete_job_manager.fail_job(job_id, current_step, str(e))


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(_: User = Depends(require_admin)):
    try:
        milvus_manager.init_collection()
        results = milvus_manager.query(
            output_fields=["filename", "file_type"],
            limit=10000,
        )

        file_stats = {}
        for item in results:
            filename = item.get("filename", "")
            file_type = item.get("file_type", "")
            if filename not in file_stats:
                file_stats[filename] = {
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_count": 0,
                }
            file_stats[filename]["chunk_count"] += 1

        profile_map = document_profile_store.get_profile_map(list(file_stats.keys()))
        for filename, profile in profile_map.items():
            if filename in file_stats:
                file_stats[filename].update(profile)

        documents = [DocumentInfo(**stats) for stats in file_stats.values()]
        return DocumentListResponse(documents=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.put("/documents/profile/batch", response_model=DocumentListResponse)
async def update_document_profiles_batch(
    request: DocumentProfileBatchUpdateRequest,
    _: User = Depends(require_admin),
):
    filenames = []
    seen = set()
    for item in request.filenames:
        key = _normalize_profile_value(item)
        if key and key not in seen:
            seen.add(key)
            filenames.append(key)
    if not filenames:
        raise HTTPException(status_code=400, detail="请至少选择一份文档")

    patch_data = _dump_profile_fields(request)
    patch_data.pop("filenames", None)
    if not patch_data:
        raise HTTPException(status_code=400, detail="请至少填写一个需要批量更新的画像字段")

    try:
        milvus_manager.init_collection()
        profile_map = document_profile_store.get_profile_map(filenames)
        missing = []
        updated_documents = []
        for key in filenames:
            stats = _get_document_stats(key)
            file_path = UPLOAD_DIR / key
            if not stats and not file_path.exists():
                missing.append(key)
                continue

            file_type = (stats or {}).get("file_type") or os.path.splitext(key)[1].lstrip(".").upper()
            payload = _build_profile_patch_payload(
                filename=key,
                file_type=file_type,
                current_profile=profile_map.get(key),
                patch_data=patch_data,
            )
            document_profile_store.upsert_profile(**payload)
            current_stats = stats or {
                "filename": key,
                "file_type": file_type,
                "chunk_count": 0,
            }
            updated_documents.append(_merge_document_profile(current_stats))

        if missing:
            raise HTTPException(status_code=404, detail=f"以下文档不存在或尚未入库: {', '.join(missing)}")
        return DocumentListResponse(documents=updated_documents)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新文档画像失败: {str(e)}")


@router.put("/documents/profile/{filename}", response_model=DocumentInfo)
async def update_document_profile(
    filename: str,
    request: DocumentProfileUpdateRequest,
    _: User = Depends(require_admin),
):
    key = _normalize_profile_value(filename)
    if not key:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    patch_data = _dump_profile_fields(request)
    if not patch_data:
        raise HTTPException(status_code=400, detail="请至少填写一个需要更新的画像字段")

    try:
        milvus_manager.init_collection()
        stats = _get_document_stats(key)
        file_path = UPLOAD_DIR / key
        if not stats and not file_path.exists():
            raise HTTPException(status_code=404, detail="文档不存在或尚未入库")

        file_type = (stats or {}).get("file_type") or os.path.splitext(key)[1].lstrip(".").upper()
        current_profile = document_profile_store.get_profile_map([key]).get(key)
        payload = _build_profile_patch_payload(
            filename=key,
            file_type=file_type,
            current_profile=current_profile,
            patch_data=patch_data,
        )
        document_profile_store.upsert_profile(**payload)

        current_stats = stats or {
            "filename": key,
            "file_type": file_type,
            "chunk_count": 0,
        }
        return _merge_document_profile(current_stats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新文档画像失败: {str(e)}")


@router.post("/documents/upload/async", response_model=DocumentUploadStartResponse)
async def upload_document_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    museum: str | None = Form(default=None),
    exhibition: str | None = Form(default=None),
    exhibit_id: str | None = Form(default=None),
    era: str | None = Form(default=None),
    category: str | None = Form(default=None),
    _: User = Depends(require_admin),
):
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if not is_supported_document(filename):
        raise HTTPException(status_code=400, detail="仅支持 PDF、Word 和 Excel 文档")

    ensure_upload_dir()
    job = upload_job_manager.create_job(filename)
    file_path = UPLOAD_DIR / filename

    try:
        upload_job_manager.update_step(job["job_id"], "upload", 1, "running", "正在保存文件到服务器")
        await save_upload_file(file, file_path)
        upload_job_manager.complete_step(job["job_id"], "upload", "文件已上传，等待后台处理")
    except Exception as e:
        upload_job_manager.fail_job(job["job_id"], "upload", f"文件保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")

    file_type = os.path.splitext(filename)[1].lstrip(".").upper()
    profile_payload = _build_profile_payload(
        filename=filename,
        file_type=file_type,
        museum=museum,
        exhibition=exhibition,
        exhibit_id=exhibit_id,
        era=era,
        category=category,
    )
    background_tasks.add_task(_process_upload_job, job["job_id"], str(file_path), filename, profile_payload)
    return DocumentUploadStartResponse(
        job_id=job["job_id"],
        filename=filename,
        message="文件已上传，正在后台解析和向量化入库",
        museum=profile_payload["museum"] or None,
        exhibition=profile_payload["exhibition"] or None,
        exhibit_id=profile_payload["exhibit_id"] or None,
        era=profile_payload["era"] or None,
        category=profile_payload["category"] or None,
    )


@router.get("/documents/upload/jobs/{job_id}", response_model=DocumentUploadJobResponse)
async def get_upload_job(job_id: str, _: User = Depends(require_admin)):
    job = upload_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="上传任务不存在或已过期")
    return DocumentUploadJobResponse(**job)


@router.get("/documents/upload/jobs", response_model=list[DocumentUploadJobResponse])
async def list_upload_jobs(_: User = Depends(require_admin)):
    jobs = upload_job_manager.list_jobs()
    jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return [DocumentUploadJobResponse(**job) for job in jobs]


@router.delete("/documents/delete/async/{filename}", response_model=DocumentDeleteStartResponse)
async def delete_document_async(
    filename: str,
    background_tasks: BackgroundTasks,
    _: User = Depends(require_admin),
):
    job = delete_job_manager.create_job(
        filename,
        steps=DELETE_STEPS,
        current_step="prepare",
        message="等待删除",
        completion_step="parent_store",
    )
    delete_job_manager.update_step(job["job_id"], "prepare", 1, "running", "删除任务已提交")
    background_tasks.add_task(_process_delete_job, job["job_id"], filename)
    return DocumentDeleteStartResponse(
        job_id=job["job_id"],
        filename=filename,
        message=f"正在删除 {filename}",
    )


@router.get("/documents/delete/jobs/{job_id}", response_model=DocumentDeleteJobResponse)
async def get_delete_job(job_id: str, _: User = Depends(require_admin)):
    job = delete_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="删除任务不存在或已过期")
    return DocumentDeleteJobResponse(**job)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    museum: str | None = Form(default=None),
    exhibition: str | None = Form(default=None),
    exhibit_id: str | None = Form(default=None),
    era: str | None = Form(default=None),
    category: str | None = Form(default=None),
    _: User = Depends(require_admin),
):
    try:
        filename = file.filename or ""
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        if not is_supported_document(filename):
            raise HTTPException(status_code=400, detail="仅支持 PDF、Word 和 Excel 文档")

        ensure_upload_dir()
        
        # Cleanup existing同名文档以保证一致性
        delete_document_transactionally(filename)

        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            new_docs = loader.load_document(str(file_path), filename)
        except Exception as doc_err:
            raise HTTPException(status_code=500, detail=f"文档处理失败: {doc_err}")

        if not new_docs:
            raise HTTPException(status_code=500, detail="文档处理失败，未能提取内容")

        parent_docs = [doc for doc in new_docs if int(doc.get("chunk_level", 0) or 0) in (1, 2)]
        leaf_docs = [doc for doc in new_docs if int(doc.get("chunk_level", 0) or 0) == 3]
        if not leaf_docs:
            raise HTTPException(status_code=500, detail="文档处理失败，未生成可检索叶子分块")

        file_type = os.path.splitext(filename)[1].lstrip(".").upper()
        profile_payload = _build_profile_payload(
            filename=filename,
            file_type=file_type,
            museum=museum,
            exhibition=exhibition,
            exhibit_id=exhibit_id,
            era=era,
            category=category,
        )
        document_profile_store.upsert_profile(**profile_payload)

        parent_chunk_store.upsert_documents(parent_docs)
        milvus_writer.write_documents(leaf_docs)

        return DocumentUploadResponse(
            filename=filename,
            chunks_processed=len(leaf_docs),
            message=(
                f"成功上传并处理 {filename}，叶子分块 {len(leaf_docs)} 个，"
                f"父级分块 {len(parent_docs)} 个（存入 PostgreSQL）"
            ),
            museum=profile_payload["museum"] or None,
            exhibition=profile_payload["exhibition"] or None,
            exhibit_id=profile_payload["exhibit_id"] or None,
            era=profile_payload["era"] or None,
            category=profile_payload["category"] or None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.delete("/documents/{filename}", response_model=DocumentDeleteResponse)
async def delete_document(filename: str, _: User = Depends(require_admin)):
    try:
        chunks_deleted = delete_document_transactionally(filename)

        return DocumentDeleteResponse(
            filename=filename,
            chunks_deleted=chunks_deleted,
            message=f"成功删除文档 {filename} 的向量数据（本地文件已保留）",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")
