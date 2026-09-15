package xiaozhi.modules.provider.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("ai_hermes_instance")
public class HermesInstanceEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    private Long tenantId;
    private Long userId;
    private String deviceId;
    private String name;
    private String baseUrl;
    private String secretRef;
    private String capabilitiesJson;
    private Integer priority;
    private Integer isEnabled;
    private Integer isHealthy;
    private Date lastHealthAt;
    private Date createdAt;
    private Date updatedAt;
}
