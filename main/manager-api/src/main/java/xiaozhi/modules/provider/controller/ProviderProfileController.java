package xiaozhi.modules.provider.controller;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.provider.entity.ProviderProfileEntity;
import xiaozhi.modules.provider.entity.ProviderSecretEntity;
import xiaozhi.modules.provider.dao.ProviderProfileDao;
import xiaozhi.modules.provider.dao.ProviderSecretDao;
import xiaozhi.modules.provider.service.ProviderProfileService;
import xiaozhi.modules.provider.service.ProviderSecretService;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "租户 Provider 管理")
@RestController
@RequestMapping("/provider")
public class ProviderProfileController {
    private final ProviderProfileService service;
    private final ProviderProfileDao profileDao;
    private final ProviderSecretDao secretDao;
    private final ProviderSecretService secretService;

    public ProviderProfileController(ProviderProfileService service, ProviderProfileDao profileDao,
            ProviderSecretDao secretDao, ProviderSecretService secretService) {
        this.service = service;
        this.profileDao = profileDao;
        this.secretDao = secretDao;
        this.secretService = secretService;
    }

    @GetMapping("/profiles")
    @Operation(summary = "获取当前用户的 Provider 配置（不返回密钥）")
    @RequiresPermissions("sys:role:normal")
    public Result<List<ProviderProfileEntity>> list() {
        UserDetail user = SecurityUser.getUser();
        return new Result<List<ProviderProfileEntity>>().ok(service.listForUser(user.getId()));
    }

    @PostMapping("/profiles")
    @Operation(summary = "新增或修改当前用户 Provider 配置")
    @RequiresPermissions("sys:role:normal")
    public Result<ProviderProfileEntity> save(@RequestBody ProviderProfileEntity request) {
        UserDetail user = SecurityUser.getUser();
        return new Result<ProviderProfileEntity>().ok(service.saveForUser(user.getId(), request));
    }

    @PostMapping("/profiles/{id}/secret")
    @Operation(summary = "写入 Provider 密钥；响应只返回掩码")
    @RequiresPermissions("sys:role:normal")
    public Result<Map<String, String>> putSecret(@PathVariable String id, @RequestBody Map<String, String> request) {
        UserDetail user = SecurityUser.getUser();
        ProviderProfileEntity profile = service.selectById(id);
        String value = request == null ? null : request.get("value");
        if (profile == null || !user.getId().equals(profile.getUserId()) || value == null || value.isBlank()) {
            return new Result<Map<String, String>>().error("Provider 配置或密钥无效");
        }
        ProviderSecretEntity secret = new ProviderSecretEntity();
        secret.setTenantId(profile.getTenantId());
        secret.setOwnerUserId(user.getId());
        secret.setSecretRef("provider:" + UUID.randomUUID());
        secret.setCiphertext(secretService.encrypt(value));
        secret.setKeyVersion("v1");
        secret.setMaskedValue(secretService.mask(value));
        secretDao.insert(secret);
        profile.setSecretRef(secret.getSecretRef());
        profileDao.updateById(profile);
        return new Result<Map<String, String>>().ok(Map.of("secretRef", secret.getSecretRef(), "maskedValue", secret.getMaskedValue()));
    }

    @DeleteMapping("/profiles/{id}")
    @Operation(summary = "删除当前用户 Provider 配置")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String id) {
        UserDetail user = SecurityUser.getUser();
        ProviderProfileEntity existing = service.selectById(id);
        if (existing != null && user.getId().equals(existing.getUserId())) {
            service.deleteById(id);
        }
        return new Result<>();
    }
}
