package xiaozhi.modules.memo.dto;

import java.util.ArrayList;
import java.util.List;

import lombok.Data;

@Data
public class MemoStateDTO {
    private Integer schemaVersion = 1;
    private Long changedAt = 0L;
    private List<MemoListDTO> lists = new ArrayList<>();
    private List<MemoTagDTO> tags = new ArrayList<>();
    private List<MemoItemDTO> items = new ArrayList<>();
}
