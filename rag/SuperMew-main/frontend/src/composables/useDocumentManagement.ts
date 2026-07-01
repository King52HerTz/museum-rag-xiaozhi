import { computed, reactive, ref, watch } from 'vue';
import { useDocumentStore } from '@/stores/documents';
import type {
  DocumentBatchApplyState,
  DocumentFilterKey,
  DocumentFilters,
  DocumentItem as ManagedDocumentItem,
  DocumentProfileKey,
  DocumentProfilePatch,
  DocumentProfilePayload,
} from '@/types/document';

const FILTER_STORAGE_KEY = 'supermew:documents:filters';
const PROFILE_KEYS: DocumentProfileKey[] = ['museum', 'exhibition', 'exhibit_id', 'era', 'category'];
const FILTER_KEYS: DocumentFilterKey[] = ['keyword', 'museum', 'exhibition', 'era', 'category'];

const createDefaultFilters = (): DocumentFilters => ({
  keyword: '',
  museum: '',
  exhibition: '',
  era: '',
  category: '',
});

const createDefaultBatchApply = (): DocumentBatchApplyState => ({
  museum: false,
  exhibition: false,
  exhibit_id: false,
  era: false,
  category: false,
});

const createDefaultBatchProfile = (): DocumentProfilePayload => ({
  museum: '',
  exhibition: '',
  exhibit_id: '',
  era: '',
  category: '',
});

const normalize = (value?: string | null) => String(value || '').trim();

export function useDocumentManagement() {
  const documentStore = useDocumentStore();
  const filters = reactive<DocumentFilters>(createDefaultFilters());
  const selectedFilenames = ref<string[]>([]);
  const batchApply = reactive<DocumentBatchApplyState>(createDefaultBatchApply());
  const batchProfile = reactive<DocumentProfilePayload>(createDefaultBatchProfile());

  const buildOptions = (pick: (doc: ManagedDocumentItem) => string | null | undefined) =>
    computed(() =>
      Array.from(
        new Set(
          documentStore.documents
            .map((doc) => normalize(pick(doc)))
            .filter((item) => item)
        )
      ).sort((a, b) => a.localeCompare(b, 'zh-CN'))
    );

  const museumOptions = buildOptions((doc) => doc.museum);
  const exhibitionOptions = buildOptions((doc) => doc.exhibition);
  const eraOptions = buildOptions((doc) => doc.era);
  const categoryOptions = buildOptions((doc) => doc.category);

  const filteredDocuments = computed(() => {
    const keyword = normalize(filters.keyword).toLowerCase();

    return documentStore.documents.filter((doc) => {
      if (filters.museum && normalize(doc.museum) !== filters.museum) return false;
      if (filters.exhibition && normalize(doc.exhibition) !== filters.exhibition) return false;
      if (filters.era && normalize(doc.era) !== filters.era) return false;
      if (filters.category && normalize(doc.category) !== filters.category) return false;

      if (!keyword) return true;

      const haystack = [
        doc.filename,
        doc.file_type,
        doc.museum,
        doc.exhibition,
        doc.exhibit_id,
        doc.era,
        doc.category,
      ]
        .map((item) => normalize(item).toLowerCase())
        .join('\n');

      return haystack.includes(keyword);
    });
  });

  const filteredFilenameList = computed(() => filteredDocuments.value.map((doc) => doc.filename));
  const selectedCount = computed(() => selectedFilenames.value.length);
  const selectedFilteredCount = computed(
    () => filteredFilenameList.value.filter((filename) => selectedFilenames.value.includes(filename)).length
  );
  const allFilteredSelected = computed(
    () =>
      filteredFilenameList.value.length > 0 &&
      filteredFilenameList.value.every((filename) => selectedFilenames.value.includes(filename))
  );

  const updateFilters = (nextFilters: DocumentFilters) => {
    FILTER_KEYS.forEach((key) => {
      filters[key] = normalize(nextFilters[key]);
    });
  };

  const resetFilters = () => {
    updateFilters(createDefaultFilters());
  };

  const restoreFilters = () => {
    try {
      const raw = localStorage.getItem(FILTER_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<Record<DocumentFilterKey, string>>;
      updateFilters({
        ...createDefaultFilters(),
        ...parsed,
      });
    } catch {
      localStorage.removeItem(FILTER_STORAGE_KEY);
    }
  };

  const persistFilters = () => {
    const payload = FILTER_KEYS.reduce((acc, key) => {
      acc[key] = normalize(filters[key]);
      return acc;
    }, {} as Record<DocumentFilterKey, string>);
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(payload));
  };

  const onRefresh = async () => {
    try {
      await documentStore.loadDocuments();
    } catch (error: any) {
      alert(error.message);
    }
  };

  const toggleSelection = (filename: string) => {
    if (selectedFilenames.value.includes(filename)) {
      selectedFilenames.value = selectedFilenames.value.filter((item) => item !== filename);
      return;
    }
    selectedFilenames.value = [...selectedFilenames.value, filename];
  };

  const toggleSelectAllFiltered = () => {
    const filtered = filteredFilenameList.value;
    if (!filtered.length) return;
    if (allFilteredSelected.value) {
      selectedFilenames.value = selectedFilenames.value.filter((item) => !filtered.includes(item));
      return;
    }
    selectedFilenames.value = Array.from(new Set([...selectedFilenames.value, ...filtered]));
  };

  const clearSelection = () => {
    selectedFilenames.value = [];
  };

  const updateBatchApply = (nextApply: DocumentBatchApplyState) => {
    PROFILE_KEYS.forEach((key) => {
      batchApply[key] = Boolean(nextApply[key]);
    });
  };

  const updateBatchProfile = (nextProfile: DocumentProfilePayload) => {
    PROFILE_KEYS.forEach((key) => {
      batchProfile[key] = normalize(nextProfile[key]);
    });
  };

  const resetBatchEditor = () => {
    updateBatchApply(createDefaultBatchApply());
    updateBatchProfile(createDefaultBatchProfile());
  };

  const submitBatchUpdate = async () => {
    if (!selectedFilenames.value.length) {
      alert('请先选择至少一份文档');
      return;
    }

    const patch: DocumentProfilePatch = {};
    PROFILE_KEYS.forEach((key) => {
      if (batchApply[key]) {
        patch[key] = normalize(batchProfile[key]);
      }
    });

    if (Object.keys(patch).length === 0) {
      alert('请先勾选至少一个需要批量更新的画像字段');
      return;
    }

    try {
      const updated = await documentStore.updateDocumentProfilesBatch(selectedFilenames.value, patch);
      resetBatchEditor();
      alert(`批量更新完成：已处理 ${updated.length} 份文档`);
    } catch (error: any) {
      alert(error.message);
    }
  };

  const initialize = async () => {
    restoreFilters();
    await onRefresh();
  };

  const cleanup = () => {
    documentStore.stopUploadJobPolling();
    documentStore.stopAllDeleteJobPolling();
  };

  watch(
    () => documentStore.documents.map((doc) => doc.filename),
    (filenames) => {
      selectedFilenames.value = selectedFilenames.value.filter((filename) => filenames.includes(filename));
    },
    { immediate: true }
  );

  watch(
    filters,
    () => {
      persistFilters();
    },
    { deep: true }
  );

  return {
    documentStore,
    filters,
    museumOptions,
    exhibitionOptions,
    eraOptions,
    categoryOptions,
    filteredDocuments,
    selectedFilenames,
    selectedCount,
    selectedFilteredCount,
    allFilteredSelected,
    batchApply,
    batchProfile,
    onRefresh,
    updateFilters,
    resetFilters,
    toggleSelection,
    toggleSelectAllFiltered,
    clearSelection,
    updateBatchApply,
    updateBatchProfile,
    resetBatchEditor,
    submitBatchUpdate,
    initialize,
    cleanup,
  };
}
