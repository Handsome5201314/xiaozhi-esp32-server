package xiaozhi.modules.provider.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_provider_profile")
@Schema(description = "租户 Provider 配置。密钥只通过 secretRef 关联服务端密文")
public class ProviderProfileEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    private Long tenantId;
    private Long userId;
    private String deviceId;
    private String capability;
    private String providerType;
    private String displayName;
    private String baseUrl;
    private String modelName;
    private String secretRef;
    private Integer priority;
    private Integer isEnabled;
    private Integer isHealthy;
    private Date createdAt;
    private Date updatedAt;
}
