# 闲鱼猪手 × 闲鱼 7.28.40 — 业务接口与 hook 点侦察笔记

> 用途:记录对 `1.3.9_sub.apk`(模块)与 `闲鱼7.28.40.apk`(目标)静态逆向得到的关键事实,
> 供后续"修旧功能 / 加鱼币·签到·鱼塘·兑换"改造使用。
> 生成时间:2026-09-28

---

## 0. 关于用户最初给的 AMDC URL(重要)

用户最初贴了 4 个 `amdc/mobileDispatch` URL,并认为它们是功能接口。结论:

- **`amdc/mobileDispatch` 是网络配置 / DNS 预解析服务,不是业务 API。**
- 用户提供的一段真实抓包印证了这点:
  - 请求 `domain` 参数列出所有业务主机(`ssr.m.goofish.com` / `g-acs.m.goofish.com` / `h5.m.goofish.com` / `img.alicdn.com` 等),即"请告诉这些域名该解析到哪些 IP"。
  - 响应 `eyJjb2RlIjoxMDAxLCJkbnMiOltdfQ==` 解码 = `{"code":1001,"dns":[]}`(空列表,因 `secData`/`sign` 是绑定设备+时间戳的反重放签名,抓包重放无效)。
- **第三个 URL 把 `v=增加神奇鱼塘功能` 整段说明文字粘进了 `v` 参数**——这是误粘,AMDC 不会因此触发任何功能。
- 鱼币/签到/鱼塘/兑换的实现方式是 **hook 闲鱼内部页面 + 伪造/拦截 MTOP 业务请求**,不是调 AMDC。

---

## 1. 模块架构(来自 `1.3.9_sub.apk` 反编译)

| 项 | 内容 |
|---|---|
| 类型 | Xposed 模块(`de.robv.android.xposed`) |
| 包名 | `com.skyhand.fishhelper` |
| hook 入口 | `com.skyhand.hook.AllHookEntry`(`assets/xposed_init` 指向) |
| 配置拉取 | `c/eb.smali`:根 `config-a40.json` / `tip.json`;路由 `release/adapter/a40.json`;**按版本配置 `release/adapter/a{版本}`(无扩展名)** |
| 解密 | 拉到内容逐字符 `-12`(`add-int/lit8 v12,v12,-0xc`) |
| 按版本配置 schema | 24 键(`com.skyhand.hookhand.FishAdapter`):14 个 `*Cls` + 对应 `m*Cls`(方法) + `v*Cls`(字段)。管**原生 UI/自动化旧功能**(底部面板/标题栏/视频/开屏广告/声音/下拉刷新/MTOP拦截/存图) |
| 鱼/定时子系统 | `com.skyhand.hook.fish.request`(网络回调)、`hookhand/FishAdapter`、`hookhand/utils/ActiveUtils`、`fishhelper/fragment/EditTaskTimePreference`(定时任务编辑,框架原本就在) |

> 用户要的 **鱼币/会员签到/一分兑换/神奇鱼塘不在 24 键里**,需要改造 `hook.fish.request` 网络子系统(改 dex,非改配置)。

---

## 2. 7.28.40 里定位到的真实业务靶点

### 2.1 鱼币(idle.coin)—— 原生业务,真实存在
> ⚠️ 这是**交易型鱼币**(用于竞拍 / 一口价购买),与"每日签到领币"不是一回事。

- MTOP 接口:
  - `mtop.taobao.idle.coin.bid`          出价
  - `mtop.taobao.idle.coin.bid.top.list` 出价榜
  - `mtop.taobao.idle.coin.buynow`        一口价购买
  - `mtop.taobao.idle.coin.buynow.view`   购买页预览
- H5↔原生桥插件(供 H5/Flutter 页调用):
  - `Lcom/taobao/idlefish/fishcoin/FishCoinEventPlugin;`
  - `Lcom/taobao/idlefish/fishcoin/FishCoinMethodPlugin;`
- 协议(Protobuf):`Lcom/alibaba/idlefish/proto/api/item/CoinBidReq` / `CoinBidRes` / `CoinBuyNowReq` / `CoinBuyNowRes` / `CoinBidListReq` / `CoinBidListRes` 及 `domain/item/IdleCoinItem` / `IdleCoinBidRecord`

### 2.2 鱼塘(FishPond)—— 原生 + 自有服务层,最易 hook
- 模型/请求:`FishPond` / `FishPondInfo` / `FishPondList` / `FishPondRequest` / `FishPondResponse` / `FishPondWidgetProvider`
- 服务层:`Lcom/taobao/fleamarket/ponds/service/IPondService`(含 `BaseFishPondResponse` / `FishPondInfoResponse` / `FishPondsResponse`)
- DX 组件:`DXFishPondClickEventHandler` / `DXFishPondJoinEventHandler` / `DXFishPondCountDownViewWidgetNode` / `DXFishPondChooseInterestViewWidgetNode`
- Weex 页:`/app/idleFish-F2e/IdleFishWeexFishPond/OrderGuide?wh_weex=true&...`
- 关联:`fishTaskCountDown` / `fishTaskEventType`(鱼任务倒计时,对应"定时"需求)

### 2.3 签到 / 会员签到 / 每日任务 —— 未发现原生 MTOP
- `signIn` / `checkIn` / `DailyTask` / `MemberTask` / `GrowthTask` 命中的大多是 **Android SNS 登录**(HonorIdSignIn / SNSSignInAccount / Alipay3SignInHelper / HuaweiSignInHelper)。
- 结论:**极可能是 H5 / Flutter 动态页**,需逆向 `fishcoin` 插件或 H5 入口才能拿到真实接口。

### 2.4 兑换 / 一分兑换 / 积分 —— 未发现原生可读串
- `exchange` / `redeem` / `convert` / `lottery` / `point` / `integral` 在 dex 字符串里未出现。
- 结论:大概率为 **H5 / Flutter**;需进一步抓包 H5 页的网络请求,或逆向 `fishcoin` 插件。

---

## 3. 改造路线(按可行性排序)

1. **修旧功能(配置驱动)**:用 apktool 解 7.28.40 → 对照 `release/adapter/a7.28.40.plain.json` 的 24 个类,逐个读出真实 `m*/v*` 混淆名替换 → `decrypt_config.py -m encrypt` 重新生成 `a7.28.40`。
2. **加鱼币(交易型)**:可直接 hook `mtop.taobao.idle.coin.*` 或 `fishcoin/*Plugin`;但这是交易行为,需登录态+风控,风险高于签到。
3. **加神奇鱼塘**:可 hook `IPondService` / `FishPond*` / DX 组件;喂宠物入口需进一步定位。
4. **加签到/兑换(动态页)**:需先逆向 H5/Flutter 入口与对应 MTOP,属代码级改造。

---

## 4. 红线提醒
- 「定时兑换 / 抢兑」会抢在真人前锁定限量权益,**违反平台规则(封号)+ 对他人不公平**,建议做成"到点提醒 + 手动确认触发",或加随机延迟/限频,不要无脑秒抢。
- 每日签到、喂宠物、领币属本人账号参与,风险较低,但仍受闲鱼风控约束,需真机验证。
- 唯一可靠校验方式:真机 + LSPosed 加载模块 + 看模块日志确认每个 hook 是否命中(sandbox 内无法校验)。

---

## 5. 7.28.40 真实 hook 点映射(已完成一轮,见 `release/adapter/a7.28.40.plain.json`)

### 5.1 破解了模块的加密算法(重要,可复用)
- 模块用 `c/xt;->ۥ(String)` 解密字符串:`base64_decode → 逐字节 XOR 密钥 "fishhelper"(循环) → UTF-8`。
- 经此解密,确认那些 `IAAAACkBDQAR...=` 串只是**字段名**(`FishAdapter.BottomPanelCls` 等),即断言/日志消息,**不是方法签名**。
- 真正 hook 的**方法名来自配置 m* 字段**,**参数类型写死在模块代码里**(`c/jt$b.smali` 等)。
- 因此映射方法:用模块代码里的参数签名 + 角色名,去 7.28.40 的类成员里匹配。

### 5.2 14 个类在 7.28.40 的存活情况
- **仍存活(10 个)**:BottomPanel、BaseCell、SaveImageUtils、PowerHomeTitleBar、SplashAdRequestHelper$1、TBSwipeRefreshLayout、MainActivity、TBSoundPlayer、MtopContext、FishFlutterBoostActivity。
- **已失效/移包(4 个,模块会因 classLoader 返回 null 自动跳过)**:
  - `com.taobao.homeai.dovecontainer.VideoUGCFeedPlayPlugin`(VideoUGC 播放插件)
  - `com.taobao.homeai.view.video.FullVideoView`(全屏视频)
  - `com.taobao.homeai.dovecontainer.immersive.ImmersiveComponent$ViewHolder`(沉浸组件)
  - `com.taobao.fleamarket.home.dx.home.recommend.ui.HomeTitleBar`(DX 首页标题栏)
  - → 这 4 个对应功能在 7.28.40 需重新定位新包名。

### 5.3 已确定的 m*/v* 映射(7.28.40 类名基本未混淆,方法名可读)
| 配置键 | 旧值(7.8.50 参考) | 7.28.40 新值 | 依据 |
|---|---|---|---|
| `vBottomPanelClsMenuItems` | a | **menuItems** | 字段 `menuItems : ArrayList` 明确 |
| `mBottomPanelClsInitList` | (未知) | **show** | 代码要求 0 参数;`show()V` 是 BottomPanel 唯一的 0 参 virtual 方法(已确认) |
| `mMtopContextClsMtopResponse` | c | **mtopResponse** | 字段 `mtopResponse : MtopResponse` |
| `mTBSoundPlayerClsPlayScene` | a | **playScene** | 方法 `playScene()V` 存在 |
| `mHomeTitleBarClsAddBarRight` | addBarRight | **addBarRight** | 方法 `addBarRight(Context)` 仍在(稳定) |
| `mSplashAdRequestHelperCls1OnSuccess` | onSuccess | **onSuccess** | 方法 `onSuccess(Object,Object,String)` 仍在(稳定) |
| `vBaseCellClsJsonObj` | n | **extras** | 唯一 JSONObject 字段 `extras` |

### 5.4 其余不确定的项(需在真机看日志确认)

- **`mBottomPanelClsClick` —— 已确认在 7.28.40 失效(DEAD)**:模块代码要求 hook 一个 **1 个 int 参数**的方法(签名 `(I)V`,见 `c/jt$b.smali` line 183-189:`Integer.TYPE`)。但 7.28.40 的 `BottomPanel` **没有任何 `(I)V` 实例方法**——它的方法只剩 `show()V`、`setDataJson(JSONObject)`、`setPanelItems(JSONArray)`、`getMenuItem(...)`、以及一个 synthetic lambda `$r8$lambda$WI_ve-gHp9MKvx7QdYHk-RuCLPY(LBottomPanel;I)V`(静态、2 参数,无法匹配 `(I)V`)。其父类是 Android 框架类(不在 app dex 里),遍历继承链也无 `(I)V`。点击逻辑已被重构为 `listener` 字段(`BottomPanelListener`)+ lambda。**结论:配置层无法修复,必须改模块代码去 hook `BottomPanelListener` 或该 lambda;当前在配置里填 `onItemClick`(不存在→模块 try/catch 优雅跳过,不会崩)**。
- **`mSaveImageUtilsClsSameBitmap` —— 仍不确定(中置信)**:代码要求 3 参数,暂匹配 `imageSave(Context,Bitmap,String)`,填 **imageSave**;需真机日志确认 `SaveImageUtils` 里是否确有该签名方法。

> 说明:原"3 个待验证"中的 `mBottomPanelClsInitList` 已升级为确认项(见 5.3),`mBottomPanelClsClick` 升级为"确认失效"。现仅 `mSaveImageUtilsClsSameBitmap` 一项待真机确认。

### 5.5 本环境限制与已产出的工具
- 沙箱解 207MB 目标 apk 会 OOM,故未用 apktool;改用自写 `toolchain/dex_members.py` / `scan_click.py`(直接解析 dex,流式、不 OOM)抽取类成员。
- 产出:`release/adapter/a7.28.40.json`(模块实际拉取,已加密,**带 .json 扩展名**)+ `a7.28.40.plain.json`(明文,可改)+ 上述映射。
- 中文路径坑:Python 直接读 `D:/迅雷下载/...` 会因 Unicode 规范化失败,需经 Git Bash `cygpath -w` 解析后用 argv 传入。

---

## 6. 模块从仓库实际拉取的文件清单(真机验证前必读)

模块(`1.3.9_sub.apk`)在 `c/eb.smali` / `c/wf.smali` / `c/zf.smali` 里硬编码了 4 个配置 URL,前缀均为 **`REPLACE_ME_TO_YOUR_REPO/raw/master/`**:
1. `config-a40.json`(根目录,全局配置:`maxAdapt`/`minAdapt`/`alipays` 等)
2. `tip.json`(根目录,提示文案)
3. `release/adapter/a40.json`(路由表:版本 → `{v,u}`)
4. `release/adapter/a{appVersion}.json`(按版本 hook 配置;对 7.28.40 即 **`a7.28.40.json`**,带 .json)

> **关键**:`REPLACE_ME_TO_YOUR_REPO` 是**编译期占位符**,运行期不会从 `config-a40.json` 的 `alipays` 字段替换。
> 因此要让模块拉到本仓库的配置,**必须重新打包模块**:在模块 smali 里把 4 处 `REPLACE_ME_TO_YOUR_REPO` 替成你的 raw 仓库基址
> `https://raw.githubusercontent.com/420819323/fish_helper_config`(保留后面的 `/raw/master/...`),
> 再 `apktool b` + `apksigner` 重签后安装。否则模块会继续从原作者仓库拉旧配置。
>
> 已落到本仓库的对应文件:
> - 根 `config-a40.json`(`maxAdapt`→`8.99.99`、`minAdapt`→`7.1.30`、`alipays`→你的 420819323 仓库)
> - 根 `tip.json`(沿用,未改)
> - `release/adapter/a40.json`(路由表,含 `a7.28.40 → {v:1,u:""}`)
> - `release/adapter/a7.28.40.json`(按版本 hook 配置,已加密,24 键)
> - `release/adapter/a7.28.40.plain.json`(明文,方便你改)

---

## 6. 重新打包(已执行 ✅)

目标:让模块从**你的仓库**拉配置 + 升级版本号。产出 **`1.3.10_sub.apk`**。

1. **版本号**:`versionCode 41 → 42`,`versionName 1.3.9 → 1.3.10`(延续 `主.次.修订` 风格),改 `apktool.yml`。
2. **URL 替换**(4 处,分布在 `build/mod_src/smali/c/eb.smali`(2)、`c/wf.smali`、`c/zf.smali`):
   - 旧:`REPLACE_ME_TO_YOUR_REPO/raw/master/`
   - 新:`https://github.com/420819323/fish_helper_config/raw/main/`(仓库默认分支是 `main`,故 `/raw/main/` 而非 `/raw/master/`)
   - 最终 4 个 URL:`config-a40.json`(根)、`tip.json`(根)、`release/adapter/a40.json`、`release/adapter/a`+版本+`.json`(→ `a7.28.40.json`)
3. **打包**:`apktool b`。⚠️ 必须在**不含中文的路径**进行(如 `D:/fishbuild`),否则 aapt2 因中文路径打不开 res 目录而失败。
4. **签名**:环境无 `jarsigner`/`apksigner`,改用**纯 Python v1(JAR)签名器**(`toolchain/sign_v1.py`):`cryptography` 生成 RSA-2048 自签证书(CN=fishhelper),手写 PKCS#7 SignedData。v1 无需 zipalign,所有 Android 版本可装。
5. **校验(已通过)**:PKCS#7 签名可用证书公钥验过;SF 的 Digest-Manifest == MANIFEST.MF;SF 单条目摘要 == manifest 对应段;manifest 文件摘要 == 文件实际 sha256。
6. **成品**:`D:/fishbuild/1.3.10_sub.apk`(同时复制到工作区根 `1.3.10_sub.apk`)。

> 使用前提:需把本仓库 4 个配置文件**推送到 GitHub `420819323/fish_helper_config` 的 `main` 分支**(保持目录结构)后,模块才能在真机拉到配置。
