import { getServiceUrl } from '../api'
import RequestService from '../httpRequest'

export default {
  list(callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/profiles`).method('GET')
      .success(callback).send()
  },
  save(profile, callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/profiles`).method('POST')
      .data(profile).success(callback).send()
  },
  putSecret(id, value, callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/profiles/${id}/secret`).method('POST')
      .data({ value }).success(callback).send()
  },
  remove(id, callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/profiles/${id}`).method('DELETE')
      .success(callback).send()
  },
  hermesList(callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/hermes`).method('GET')
      .success(callback).send()
  },
  hermesSave(instance, callback, failCallback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/hermes`).method('POST')
      .data(instance).success(callback).fail(failCallback).send()
  },
  hermesPutSecret(id, value, callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/hermes/${id}/secret`).method('POST')
      .data({ value }).success(callback).send()
  },
  hermesRemove(id, callback) {
    RequestService.sendRequest().url(`${getServiceUrl()}/provider/hermes/${id}`).method('DELETE')
      .success(callback).send()
  }
}
