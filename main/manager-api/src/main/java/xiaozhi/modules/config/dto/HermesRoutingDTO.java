package xiaozhi.modules.config.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class HermesRoutingDTO {
    @NotNull
    private Long tenantId;
    @NotNull
    private Long userId;
    private String deviceId;
}
