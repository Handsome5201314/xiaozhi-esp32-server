package xiaozhi.modules.memo.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.memo.dto.MemoStateDTO;
import xiaozhi.modules.memo.dto.MemoSyncResultDTO;
import xiaozhi.modules.memo.service.MemoSyncService;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "便单同步")
@RestController
@AllArgsConstructor
@RequestMapping("/memo")
public class MemoController {
    private final MemoSyncService memoSyncService;

    @GetMapping("/state")
    @Operation(summary = "获取当前用户便单完整状态")
    @RequiresPermissions("sys:role:normal")
    public Result<MemoStateDTO> getState() {
        return new Result<MemoStateDTO>().ok(memoSyncService.getState(SecurityUser.getUserId()));
    }

    @PostMapping("/sync")
    @Operation(summary = "同步当前用户便单状态")
    @RequiresPermissions("sys:role:normal")
    public Result<MemoSyncResultDTO> sync(@RequestBody(required = false) MemoStateDTO state) {
        return new Result<MemoSyncResultDTO>().ok(memoSyncService.syncState(SecurityUser.getUserId(), state));
    }

    @GetMapping("/changes")
    @Operation(summary = "获取当前用户便单变更，v1 返回完整状态")
    @RequiresPermissions("sys:role:normal")
    public Result<MemoStateDTO> getChanges(@RequestParam(value = "since", required = false) Long since) {
        return new Result<MemoStateDTO>().ok(memoSyncService.getState(SecurityUser.getUserId()));
    }
}
