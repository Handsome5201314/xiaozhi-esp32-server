package xiaozhi.modules.config.controller;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.config.dto.AgentModelsDTO;
import xiaozhi.modules.config.dto.CorrectWordsDTO;
import xiaozhi.modules.config.dto.HermesRoutingDTO;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.provider.dao.HermesInstanceDao;
import xiaozhi.modules.provider.dao.ProviderSecretDao;
import xiaozhi.modules.provider.entity.HermesInstanceEntity;
import xiaozhi.modules.provider.entity.ProviderSecretEntity;
import xiaozhi.modules.provider.service.ProviderSecretService;
import xiaozhi.modules.device.dao.DeviceDao;
import java.util.ArrayList;
import java.util.Map;

/**
 * xiaozhi-server 配置获取
 *
 * @since 1.0.0
 */
@RestController
@RequestMapping("config")
@Tag(name = "参数管理")
@AllArgsConstructor
public class ConfigController {
    private final ConfigService configService;
    private final HermesInstanceDao hermesInstanceDao;
    private final ProviderSecretDao providerSecretDao;
    private final ProviderSecretService providerSecretService;
    private final DeviceDao deviceDao;

    @PostMapping("server-base")
    @Operation(summary = "服务端获取配置接口")
    public Result<Object> getConfig() {
        Object config = configService.getConfig(true);
        return new Result<Object>().ok(config);
    }

    @PostMapping("agent-models")
    @Operation(summary = "获取智能体模型")
    public Result<Object> getAgentModels(@Valid @RequestBody AgentModelsDTO dto) {
        // 效验数据
        ValidatorUtils.validateEntity(dto);
        Object models = configService.getAgentModels(dto.getMacAddress(), dto.getSelectedModule());
        return new Result<Object>().ok(models);
    }

    @PostMapping("correct-words")
    @Operation(summary = "获取智能体替换词")
    public Result<Object> getCorrectWords(@Valid @RequestBody CorrectWordsDTO dto) {
        ValidatorUtils.validateEntity(dto);
        List<String> list = configService.getCorrectWords(dto.getMacAddress());
        return new Result<Object>().ok(list);
    }

    @PostMapping("hermes-routing")
    @Operation(summary = "服务端获取租户 Hermes 路由")
    public Result<Object> getHermesRouting(@Valid @RequestBody HermesRoutingDTO dto) {
        if (dto.getDeviceId() == null || dto.getDeviceId().isBlank()
                || deviceDao.selectOne(new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<xiaozhi.modules.device.entity.DeviceEntity>()
                        .and(w -> w.eq("id", dto.getDeviceId()).or().eq("mac_address", dto.getDeviceId()))
                        .eq("user_id", dto.getUserId()).eq("tenant_id", dto.getTenantId())) == null) {
            return new Result<Object>().error("设备不属于当前用户或租户");
        }
        var query = new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<HermesInstanceEntity>()
                .eq("tenant_id", dto.getTenantId()).and(w -> w.eq("user_id", dto.getUserId()).or().isNull("user_id"))
                .eq("is_enabled", 1).eq("is_healthy", 1)
                .orderByAsc("priority", "id");
        if (dto.getDeviceId() == null || dto.getDeviceId().isBlank()) {
            query.isNull("device_id");
        } else {
            query.and(w -> w.eq("device_id", dto.getDeviceId()).or().isNull("device_id"));
        }
        var result = new ArrayList<Map<String, Object>>();
        for (HermesInstanceEntity instance : hermesInstanceDao.selectList(query)) {
            Map<String, Object> item = new java.util.HashMap<>();
            item.put("id", instance.getId());
            item.put("tenantId", instance.getTenantId());
            item.put("userId", instance.getUserId());
            item.put("deviceId", instance.getDeviceId());
            item.put("name", instance.getName());
            item.put("baseUrl", instance.getBaseUrl());
            item.put("model", instance.getModel());
            item.put("capabilitiesJson", instance.getCapabilitiesJson());
            item.put("toolPermissionsJson", instance.getToolPermissionsJson());
            item.put("priority", instance.getPriority());
            item.put("secretRef", instance.getSecretRef());
            if (instance.getSecretRef() != null) {
                ProviderSecretEntity secret = providerSecretDao.selectOne(
                        new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<ProviderSecretEntity>()
                                .eq("secret_ref", instance.getSecretRef()).eq("tenant_id", dto.getTenantId()));
                if (secret != null) item.put("secret", providerSecretService.decrypt(secret.getCiphertext()));
            }
            result.add(item);
        }
        return new Result<Object>().ok(result);
    }
}
