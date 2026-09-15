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
  }
}
