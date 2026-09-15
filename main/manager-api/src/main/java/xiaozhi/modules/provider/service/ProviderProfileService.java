package xiaozhi.modules.provider.service;

import java.util.List;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.provider.entity.ProviderProfileEntity;

public interface ProviderProfileService extends BaseService<ProviderProfileEntity> {
    List<ProviderProfileEntity> listForUser(Long userId);
    ProviderProfileEntity saveForUser(Long userId, ProviderProfileEntity request);
}
