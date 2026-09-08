import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

function request(method, path, data, callback, errorCallback) {
  const builder = RequestService.sendRequest()
    .url(`${getServiceUrl()}/museum/exhibits${path}`)
    .method(method);
  if (data !== undefined) builder.data(data);
  builder.success((res) => {
    RequestService.clearRequestTime();
    if (callback) callback(res);
  }).fail(errorCallback).send();
}

export default {
  list(params, callback, errorCallback) {
    request('GET', '', params, callback, errorCallback);
  },
  create(data, callback, errorCallback) {
    request('POST', '', data, callback, errorCallback);
  },
  update(id, data, callback, errorCallback) {
    request('PUT', `/${encodeURIComponent(id)}`, data, callback, errorCallback);
  },
  changeStatus(id, status, callback, errorCallback) {
    request('POST', `/${encodeURIComponent(id)}/status/${encodeURIComponent(status)}`, undefined, callback, errorCallback);
  },
  remove(id, callback, errorCallback) {
    request('DELETE', `/${encodeURIComponent(id)}`, undefined, callback, errorCallback);
  }
};
