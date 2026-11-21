"""准备 shader 背景所需的库：python3 tools/vendor_shaders.py [版本]
从 jsDelivr 取 `shaders@<版本>` 的 core 入口（已打包成单文件 ES 模块，约 2.5MB，MIT 许可），存到 web/vendor/shaders-core.js。
只需做一次；不需要 node / npm。校验：文件里必须有 createRendererFromJSON 与 deltaSeconds（逐帧确定性渲染的关键接口，v4.0.2 起提供）。"""
import sys, urllib.request
from common import ROOT

ver = sys.argv[1] if len(sys.argv) > 1 else '4.0.2'
url = f'https://cdn.jsdelivr.net/npm/shaders@{ver}/dist/core/index.js/+esm'
dst = ROOT / 'web' / 'vendor' / 'shaders-core.js'
dst.parent.mkdir(parents=True, exist_ok=True)
print('下载', url)
data = urllib.request.urlopen(url, timeout=120).read()
text = data.decode('utf-8', 'replace')
for must in ('createRendererFromJSON', 'deltaSeconds', 'setFrameLocked'):
    if must not in text:
        sys.exit(f'下载的文件里没有 {must}：版本 {ver} 可能不支持帧锁定渲染，请用 >= 4.0.2')
dst.write_bytes(data)
print(f'已保存 {dst}（{len(data) / 1e6:.1f} MB）。授权：MIT，©  Shader Effects, Inc.（https://github.com/shader-effects-inc/shaders）')
