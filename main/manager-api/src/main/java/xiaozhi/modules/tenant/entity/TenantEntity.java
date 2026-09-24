package xiaozhi.modules.tenant.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("ai_tenant")
public class TenantEntity {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String name;
    private String status;
    private String planCode;
    private String policyJson;
    private Date createdAt;
    private Date updatedAt;
}
