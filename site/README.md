# GeoTask项目门户与案例体验站

`site/`是GeoTask的纯静态公共站点，包含项目总门户、GT01—GT26互动案例、`robots.txt`和`sitemap.xml`。

站点没有后台、统计脚本、Cookie、账号系统、模型密钥或外部JavaScript依赖。案例页只在浏览器中复制任务、执行局部确定性复算，并跳转到用户选择的大模型平台。

## 信息架构

```text
site/index.html          GeoTask项目总门户
site/gt01/index.html     GT01两点距离体验
site/gt02/index.html     GT02独立验证体验
...
site/gt13/index.html     GT13车辆安全包络体验
site/gt14/index.html     GT14应急救援最快到达体验
site/gt15/index.html     GT15巡检机器人实时障碍体验
site/gt16/index.html     GT16无人机计划验证与动态监测体验
site/gt17/index.html     GT17城市事件多源上报去重体验
site/gt18/index.html     GT18救援机器人安全路线体验
site/gt19/index.html     GT19无人机地面净空投放体验
site/gt20/index.html     GT20车辆绿灯下游阻塞体验
site/gt21/index.html     GT21同目标Observation冲突策略体验
site/gt22/index.html     GT22首个World State快照体验
site/gt23/index.html     GT23无人机连续飞行状态变化体验
site/gt24/index.html     GT24临时禁飞区影响范围体验
site/gt25/index.html     GT25局部安全距离重算体验
site/gt26/index.html     GT26飞行服务站营业时间限定纠偏体验
site/robots.txt          搜索引擎规则
site/sitemap.xml         门户与GT01—GT26索引
```

根地址始终代表GeoTask项目本身，不再代表某一个案例。每个案例使用独立稳定地址，并提供返回项目首页的入口。

## 当前案例

- `GT01`：计算`(0,0)`与`(3,4)`之间的距离，结果为`ab_distance = 5.0 meter`
- `GT02`：比较模型结果与浏览器本地确定性结果`144.22 meter`
- `GT03`：四点折线的最后一段进入矩形限制区，结果为`route_intersects_zone = true`
- `GT04`：二维投影相同但高度区间分离，结果为`altitude_conflict = false`
- `GT05`：空间和高度相同但时间分离，结果为`temporal_conflict = false`
- `GT06`：路线和高度条件为true、时间条件为false，显式AND得到`full_conflict = false`
- `GT07`：时间条件无法核验，三值逻辑传播`unknown`
- `GT08`：不可核验条件触发结构化证据请求、阻断输出和恢复条件
- `GT09`：两份已核验临时禁飞通知产生冲突，进入证据冲突复核
- `GT10`：两台机器人争用单容量窄通道，根据显式优先级生成`robot_b_wait`
- `GT11`：目标直线距离50米，但轮式机器人可达网络路线为300米
- `GT12`：合法绕飞路线加安全余量超过无人机剩余航程
- `GT13`：道路开放但施工通道2.4米，小于车辆2.7米安全包络
- `GT14`：救援队A距离更近但14分钟到达，救援队B只需8分钟并满足12分钟响应时限
- `GT15`：静态地图显示通道可通行，但实时托盘障碍与路线相交，机器人必须停车并重新规划
- `GT16`：初始交叉计划满足时间间隔，但新遥测使预测间隔从120秒缩至80秒，系统保留当前通行结论并进入持续监测
- `GT17`：同一积水事件被十个来源连续上报，系统合并为一个处置任务并保留十份来源证据
- `GT18`：120米最短路线穿过120℃高温区，超过救援机器人80℃耐受上限，需改走260米安全路线
- `GT19`：无人机已到达目标上空，但落点人员净空只有10米，低于30米最低投放要求，需悬停并请求清场
- `GT20`：车辆已获得绿灯，但下游出口仅剩4米，低于整车与安全缓冲所需6.8米，需在停止线前等待
- `GT21`：遥测显示延误60秒、运行审核记录显示55秒；页面先说明静默覆盖、取平均和擅自判断来源权威会造成什么业务风险，再在技术折叠区解释失败关闭与显式优先级
- `GT22`：无人机位置和电量来自两个系统；页面先说明对象、时间和字段可能被错误拼接，再展示如何形成同一时刻、可追溯的统一运行快照
- `GT23`：无人机飞行五分钟后位置与电量发生变化；页面先说明覆盖最新值为何无法证明状态变化，再展示前后快照、300秒时间差和3项显式变化的绑定
- `GT24`：临时禁飞区在14:00—16:00生效；医疗航线穿越、巡检航线绕开，页面展示如何只将医疗航线、任务、审批和起飞动作纳入有限复核链
- `GT25`：无人机从走廊100米移动到130米；页面展示如何只重算20米和130米两项相关距离，并保留110米固定设施间距与48%电池余量
- `GT26`：飞行服务站营业时间从08:00—22:00调整为09:00—18:00；页面展示如何只替换营业计划、保留四项站点信息，并阻断20:30任务直至复核

## 公共访问地址

GitHub Pages是公共Canonical入口：

- <https://stpku.github.io/GeoTask/>
- <https://stpku.github.io/GeoTask/gt01/>
- <https://stpku.github.io/GeoTask/gt02/>
- <https://stpku.github.io/GeoTask/gt03/>
- <https://stpku.github.io/GeoTask/gt04/>
- <https://stpku.github.io/GeoTask/gt05/>
- <https://stpku.github.io/GeoTask/gt06/>
- <https://stpku.github.io/GeoTask/gt07/>
- <https://stpku.github.io/GeoTask/gt08/>
- <https://stpku.github.io/GeoTask/gt09/>
- <https://stpku.github.io/GeoTask/gt10/>
- <https://stpku.github.io/GeoTask/gt11/>
- <https://stpku.github.io/GeoTask/gt12/>
- <https://stpku.github.io/GeoTask/gt13/>
- <https://stpku.github.io/GeoTask/gt14/>
- <https://stpku.github.io/GeoTask/gt15/>
- <https://stpku.github.io/GeoTask/gt16/>
- <https://stpku.github.io/GeoTask/gt17/>
- <https://stpku.github.io/GeoTask/gt18/>
- <https://stpku.github.io/GeoTask/gt19/>
- <https://stpku.github.io/GeoTask/gt20/>
- <https://stpku.github.io/GeoTask/gt21/>
- <https://stpku.github.io/GeoTask/gt22/>
- <https://stpku.github.io/GeoTask/gt23/>
- <https://stpku.github.io/GeoTask/gt24/>
- <https://stpku.github.io/GeoTask/gt25/>
- <https://stpku.github.io/GeoTask/gt26/>

当前开发镜像：

- <https://skyswind.tailf4fad8.ts.net/geotask/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt01/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt02/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt03/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt04/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt05/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt06/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt07/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt08/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt09/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt10/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt11/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt12/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt13/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt14/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt15/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt16/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt17/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt18/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt19/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt20/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt21/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt22/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt23/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt24/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt25/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt26/>

公共仓库：<https://github.com/stpku/GeoTask>

## GitHub Pages部署

`.github/workflows/pages.yml`在公共仓`main`分支更新后发布完整`site/`目录。仓库Settings > Pages的Source应设置为GitHub Actions。

工作流上传路径必须保持：

```text
site
```

站点使用相对链接，可以直接部署在`/GeoTask/`项目子路径下。

## Nginx部署

必须同步完整目录，而不是只处理根页：

```bash
sudo rsync -a --delete site/ /var/www/geotask-experience/
test -f /var/www/geotask-experience/index.html
test -f /var/www/geotask-experience/gt01/index.html
test -f /var/www/geotask-experience/gt02/index.html
test -f /var/www/geotask-experience/gt13/index.html
test -f /var/www/geotask-experience/gt14/index.html
test -f /var/www/geotask-experience/gt15/index.html
test -f /var/www/geotask-experience/gt16/index.html
test -f /var/www/geotask-experience/gt17/index.html
test -f /var/www/geotask-experience/gt18/index.html
test -f /var/www/geotask-experience/gt19/index.html
test -f /var/www/geotask-experience/gt20/index.html
test -f /var/www/geotask-experience/gt21/index.html
test -f /var/www/geotask-experience/gt22/index.html
test -f /var/www/geotask-experience/robots.txt
test -f /var/www/geotask-experience/sitemap.xml
```

仓库中的`site/deploy-nginx.sh`会读取生成的`site/cases.txt`，逐一检查目录中的全部公开案例、robots、sitemap和导航索引，再验证并重载Nginx。案例清单不再手工写入部署脚本。

新增案例先运行脚手架预览：

```bash
python tools/scaffold_case.py \
  --stage action_feasibility \
  --case-key uav-weather-diversion \
  --title-zh "天气恶化后，无人机为什么不能继续直飞？" \
  --summary-zh "核验天气证据变化后，原飞行动作是否仍然可执行。"
```

确认后追加`--write`。脚手架只要求4个作者输入：`cases/catalog.yaml`、案例示例YAML、案例体验页和一个合并测试文件；门户、Sitemap、部署列表和导航索引自动生成。脚手架输出是标记明确的可运行starter，发布前必须替换示例距离、对象、约束、候选动作和测试。

跨案例元数据统一维护在`cases/catalog.yaml`。单独修改目录后运行：

```bash
python tools/generate_case_catalog.py --write
python tools/generate_case_catalog.py --check
```

生成器会同步更新门户案例区、`site/sitemap.xml`、`site/cases.txt`、`site/cases.json`，并为每个案例页注入`site/assets/case-shared.css`和`site/assets/case-navigation.js`。共享脚本从同源`cases.json`生成“上一例—全部案例—下一例”导航；原页面链接继续保留为离线降级路径。

推荐配置：

```nginx
location = /geotask {
    return 301 /geotask/;
}

location /geotask/ {
    alias /var/www/geotask-experience/;
    index index.html;
    autoindex off;
    add_header Cache-Control "no-cache";
}
```

不要配置把所有缺失路径回退到`/geotask/index.html`的规则，否则会用项目门户掩盖丢失的案例文件。

部署后：

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I https://skyswind.tailf4fad8.ts.net/geotask/
curl -I https://skyswind.tailf4fad8.ts.net/geotask/gt01/
curl -I https://skyswind.tailf4fad8.ts.net/geotask/gt13/
```

## 发布原则

- GitHub Pages作为公共Canonical入口和长期备份；
- 开发镜像用于内部验收和国内访问测试；
- 微信文章的“阅读原文”直接链接对应GT案例，不再把根地址当作GT01；
- 新增案例优先使用`tools/scaffold_case.py`，作者只维护目录条目、示例YAML、体验页和合并测试；门户、Sitemap、部署列表和导航索引由生成器同步；
- 任何静态文件中都不得写入模型密钥、客户数据或内部路径。
