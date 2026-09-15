package xiaozhi.modules.provider.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("ai_provider_secret")
public class ProviderSecretEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    private Long tenantId;
    private Long ownerUserId;
    private String secretRef;
    private String ciphertext;
    private String keyVersion;
    private String maskedValue;
    private Date createdAt;
    private Date updatedAt;
}
