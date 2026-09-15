package xiaozhi.modules.provider.controller;

import java.util.List;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.provider.entity.HermesInstanceEntity;
import xiaozhi.modules.provider.service.HermesInstanceService;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "Hermes 实例管理")
@RestController
@RequestMapping("/provider/hermes")
public class HermesInstanceController {
    private final HermesInstanceService service;

    public HermesInstanceController(HermesInstanceService service) { this.service = service; }

    @GetMapping
    @RequiresPermissions("sys:role:normal")
    @Operation(summary = "获取当前用户 Hermes 实例")
    public Result<List<HermesInstanceEntity>> list() {
        UserDetail user = SecurityUser.getUser();
        return new Result<List<HermesInstanceEntity>>().ok(service.listForUser(user.getId()));
    }

    @PostMapping
    @RequiresPermissions("sys:role:normal")
    @Operation(summary = "新增或修改 Hermes 实例")
    public Result<HermesInstanceEntity> save(@RequestBody HermesInstanceEntity request) {
        UserDetail user = SecurityUser.getUser();
        return new Result<HermesInstanceEntity>().ok(service.saveForUser(user.getId(), request));
    }

    @DeleteMapping("/{id}")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String id) {
        HermesInstanceEntity entity = service.selectById(id);
        UserDetail user = SecurityUser.getUser();
        if (entity != null && user.getId().equals(entity.getUserId())) service.deleteById(id);
        return new Result<>();
    }
}
