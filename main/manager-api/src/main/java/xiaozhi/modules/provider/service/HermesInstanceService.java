package xiaozhi.modules.provider.service;

import java.util.List;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.provider.entity.HermesInstanceEntity;
import java.util.Map;

public interface HermesInstanceService extends BaseService<HermesInstanceEntity> {
    List<HermesInstanceEntity> listForUser(Long userId);
    HermesInstanceEntity saveForUser(Long userId, HermesInstanceEntity request);
    Map<String, String> putSecretForUser(Long userId, String id, String value);
}
