# 数据访问边界

本项目不把“能找到元数据”写成“已下载产品”。当前可复现实验只使用两份真实数据：

- ISMN 的 TUW-GEO 官方 Python 包仓库公开测试数据，作为唯一地面验证值；
- Open-Meteo 历史接口明确指定 `models=era5` 获得的 ERA5 点尺度数据，作为气象驱动、稀疏观测与基线。

## 完整科研版本需要的凭据

| 数据 | 推荐正式入口 | 访问约束 | 本 MVP 状态 |
|---|---|---|---|
| SMAP L3/L4 | NASA Earthdata / NSIDC | Earthdata Login | 未下载，不伪造 |
| GLDAS/Noah | NASA GES DISC | Earthdata Login | 未下载，不伪造 |
| ISMN 批量站点 | ISMN Data Portal | 注册并接受数据条款 | 仅用公开测试站 |
| ERA5/ERA5-Land | Copernicus CDS API | CDS 账户和 API key | 使用 ERA5 镜像点数据 |
| Sentinel-1/2 | Copernicus Data Space | OAuth；公共 STAC 视服务而定 | 点尺度 MVP 未使用 |

完整版本应将凭据放在环境变量或本机密钥存储中，禁止提交 `.netrc`、token、CDS key。每个下载文件必须记录 URL、时间、字节数、SHA-256、产品版本和质量标志。

## 尺度纪律

ARM-1 cosmic-ray probe 的代表深度、ERA5 0–7 cm 网格和未来 SMAP/Sentinel 足迹并不相同。进入多源实验前必须增加 footprint aggregation、representativeness error 和 station-to-grid mapping；否则只能报告点尺度管线结果。
