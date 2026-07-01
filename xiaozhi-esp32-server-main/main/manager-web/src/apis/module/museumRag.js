import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

function request({ url, method = 'GET', data, headers = {}, callback, errorCallback }) {
  const builder = RequestService.sendRequest()
    .url(url)
    .method(method)
    .header(headers);

  if (data !== undefined) {
    builder.data(data);
  }

  builder
    .success((res) => {
      RequestService.clearRequestTime();
      callback && callback(res);
    })
    .fail((err) => {
      errorCallback && errorCallback(err);
    })
    .networkFail(() => {
      RequestService.reAjaxFun(() => {
        request({ url, method, data, headers, callback, errorCallback });
      });
    })
    .send();
}

export default {
  getWorkbenchLoginUrl(callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/workbench-login-url`,
      method: 'GET',
      callback,
      errorCallback
    });
  },

  listDocuments(callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/documents`,
      method: 'GET',
      callback,
      errorCallback
    });
  },

  uploadDocument(file, callback, errorCallback) {
    const formData = new FormData();
    formData.append('file', file);
    request({
      url: `${getServiceUrl()}/museum/rag/documents/upload`,
      method: 'POST',
      data: formData,
      headers: {},
      callback,
      errorCallback
    });
  },

  listUploadJobs(callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/documents/upload/jobs`,
      method: 'GET',
      callback,
      errorCallback
    });
  },

  getUploadJob(jobId, callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/documents/upload/jobs/${encodeURIComponent(jobId)}`,
      method: 'GET',
      callback,
      errorCallback
    });
  },

  deleteDocument(filename, callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/documents/${encodeURIComponent(filename)}`,
      method: 'DELETE',
      callback,
      errorCallback
    });
  },

  getDeleteJob(jobId, callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/documents/delete/jobs/${encodeURIComponent(jobId)}`,
      method: 'GET',
      callback,
      errorCallback
    });
  },

  query(data, callback, errorCallback) {
    request({
      url: `${getServiceUrl()}/museum/rag/query`,
      method: 'POST',
      data,
      headers: { 'content-type': 'application/json; charset=utf-8' },
      callback,
      errorCallback
    });
  }
};
