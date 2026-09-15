package xiaozhi.modules.memo.dto;

import lombok.Data;

@Data
public class MemoListDTO {
    private String id = "";
    private String name = "";
    private String color = "#1e7a72";
    private Long createdAt = 0L;
    private Long updatedAt = 0L;
    private Long deletedAt = 0L;
    private Long order = 0L;
}
