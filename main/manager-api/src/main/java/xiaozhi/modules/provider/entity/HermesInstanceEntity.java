package xiaozhi.modules.provider.entity;

import java.util.Date;

import com.fasterxml.jackson.annotation.JsonProperty;
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
    private String model;
    private String secretRef;
    @JsonProperty("capabilities")
    private String capabilitiesJson;
    private Integer priority;
    private Integer isEnabled;
    private Integer isHealthy;
    private Date lastHealthAt;
    private String toolPermissionsJson;
    private Integer summaryReceiveEnabled;
    private Date lastSummaryAt;
    private String lastSummaryError;
    private Date createdAt;
    private Date updatedAt;
}
