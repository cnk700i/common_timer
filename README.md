# 备注
使用说明见[个人blog](https://ljr.im/articles/plugin-home-assistant-general-timer-upgrade/)

# 更新日志

2020-08-12
1. 适配Home Assistant 0.114.0

2020-06-14
1. 适配Home Assistant 0.111.2

2019-09-07
1. HA 0.98.3版本下测试
2. 修复使用集成（例如ESPHOME）影响插件正常初始化问题。

2019-09-04
1. 使用新方法创建内置用户（某个版本后需要用户权限才能调service控制设备）。

2019-08-27
1. 完善调用自定义服务功能，支持使用common_timer.set设置。
2. 增加外部操作中断循环任务配置项。
3. 调式修复若干bug。
4. 界面设备类型中文化。

2019-08-23
1. HA 0.97.2版本下测试，为小度音箱定时控制调用自定义服务增加功能支持、修复循环控制失效bug。

2019-05-05
1. 适配0.92.1，使用lovelace界面请设置info_num_min、info_num_max为一样。

---v3_0.85.1_temp ---
1. 增加点击排序，面板列表的设备，执行多的会排前面。

2. 增加保存任务信息功能，每次HA正常重启会保存到{[HA配置目录]}/.storage/common_timer_tasks。

3. 可自定义设备的周期任务时间比例，方法见上面小节。

---v3_0.77.3---
1. 增加了周期运行任务

- 开发这个功能的目的是，想让家里暗卫的排风扇定期工作，保证暗卫的排风时间：开启一会，然后关闭一会，再开启，这样往复工作。
- 为了方便，设置了人工介入操作则会中断周期任务。

2. 增加了配置项

- 虽然并不能全部自定义配置。其实一开始目标是全部可配置的，不过感觉没什么用，于是做一半做做样子算了-。-

3. 整理了一下代码

- 塑料英文注释，请意会。

4. 增加了服务调用方法

- 这样就像个插件了。。。

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
  pattern: '[\u4e00-\u9fa5]+'  # 注意：默认筛选friendly_name包含中文的设备，如果不筛选，设置为'.*'
  name: ct_control_panel  # 控制面板的名称，需英文。如果有自定义分组页面，需把对应的group，例如goup.ct_control_panel加到分页
  friendly_name: 通用定时器  # 控制面板别名
  ratio: 5  # 时间比例，只用于周期任务：开⇌关[1:x]表示开状态设置1分钟，则关状态x分钟；关⇌开[1:x]表示关状态设置1分钟，则开状态x分钟
  info_panel:
    name: ct_info_panel  # 任务列表面板名称，需英文。如果有自定义分组页面，需把对应的group，例如group.ct_info_panel加到分页
    friendly_name: 定时任务列表  #任务面板别名
    info_num_min: 1  # 任务列表面板常驻显示最小行
    info_num_max: 10  # 任务列表面板常驻显示最大行。注：如果最大最小设置一致，则常驻显示
  linked_user: common_timer_linked_user # 插件关联用户名，由插件自动创建，用于解决控制需要权限问题
  interrupt_loop: False # 外部操作是否中断循环任务
```
>注：如果只配置`common_timer:`，则会默认按上面的样板配置进行设置;使用lovelace界面请设置info_num_min、info_num_max为一样。
## 关于input_select、input_text、input_boolean组件说明
新版本插件将input_select、input_text、input_boolean也放了进来，这样不用改安装目录下这三个文件，避免升级版本后修改失效；也更方便使用docker部署方式修改，docker部署方式一般只映射配置目录。如Home Assistant后续版本更新了以上三个组件，可按以下方法进行更新：
1. 找到组件文件：安装后在{[HA安装目录]}/components/；或者去官方github相应的版本分支（tags）/homeassistant/components/
2. 拷贝组件到{[HA配置目录]}/custom_components目录下
2. 找到各自目录里的__init__.py，将`async def async_setup(hass, config):`中的 `component= EntityComponent(_LOGGER, DOMAIN, hass)` 更改为 `component = hass.data[DOMAIN] = EntityComponent(_LOGGER, DOMAIN, hass)`

# 周期任务时间比例自定义
面板就不放配置项了，不常用的功能。步骤：
1、正常运行一次任务，重启保存配置文件
2、{[HA配置目录]}/.storage/common_timer_tasks，在tasks:{}里面修改对应的entity_id的ratio值即可
3、再重启生效

# 调试
根据[教程][1]查看插件运行日志

[1]: https://ljr.im/articles/home-assistant-novice-question-set/#3-%E8%B0%83%E8%AF%95%E5%8F%8A%E6%9F%A5%E7%9C%8B%E7%A8%8B%E5%BA%8F%E8%BF%90%E8%A1%8C%E6%97%A5%E5%BF%97 "调试及查看程序运行日志"
