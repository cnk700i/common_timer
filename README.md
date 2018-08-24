# 配置说明（configuration.yaml）
```yaml
common_timer:
  domains:  # 筛选设备（component）类型
    - light
    - automation
    - switch
    - script
    - input_boolean
  exclude:  # 排除设备，使用entity_id
    - light.test
  pattern: '[\u4e00-\u9fa5]+'  # 筛选friendly_name包含中文的设备，如果不筛选，设置为'.*'
  name: ct_control_panel  # 控制面板的名称，需英文。如果有自定义分组页面，需把对应的group，例如goup.ct_control_panel加到分页
  friendly_name: 通用定时器  # 控制面板别名
  ratio: 5  # 时间比例，只用于周期任务：开⇌关[1:x]表示开状态设置1分钟，则关状态x分钟；关⇌开[1:x]表示关状态设置1分钟，则开状态x分钟
  info_panel:
    name: ct_info_panel  # 任务列表面板名称，需英文。如果有自定义分组页面，需把对应的group，例如group.ct_info_panel加到分页
    friendly_name: 定时任务列表  #任务面板别名
    info_num_min: 1  # 任务列表面板常驻显示最小行
    info_num_max: 10  # 任务列表面板常驻显示最大行。注：如果最大最小设置一致，则常驻显示
```
>注：如果只配置`common_timer:`，则会默认按上面的样板配置进行设置。

# 更新

1. 增加了周期运行任务

- 开发这个功能的目的是，想让家里暗卫的排风扇定期工作，保证暗卫的排风时间：开启一会，然后关闭一会，再开启，这样往复工作。
- 为了方便，设置了人工介入操作则会中断周期任务。

2. 增加了配置项

- 虽然并不能全部自定义配置。其实一开始目标是全部可配置的，不过感觉没什么用，于是做一半做做样子算了-。-

3. 整理了一下代码

- 塑料英文注释，请意会。

4. 增加了服务调用方法

- 这样就像个插件了。。。
