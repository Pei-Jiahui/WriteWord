​1. 项目愿景 (Project Vision)
​打造一个极简、垂直的 Web 工具，帮助学生将电子文本转换为高度真实的模拟手写图像。核心竞争力在于**“免费+真实”**（通过模拟涂改痕迹和字迹抖动来规避机器感）。
​2. 技术栈 (Tech Stack)
​Backend: Python 3.10+ (核心逻辑：Pillow/OpenCV 用于图像合成)
​Frontend: Vue 3 (Vite + Composition API + Tailwind CSS)
​通信: REST API (Flask 或 FastAPI)
​部署目标: 适配广告嵌入的单页应用 (SPA)
​3. 启动步骤 (Getting Started)

### 后端
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 放入手写字体文件到 backend/fonts/（默认读取 handwriting.ttf）

# 3. 启动 API 服务（二选一）
python backend/app.py
# 或
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

API 服务默认监听 http://localhost:8000
- 健康检查: GET /api/health
- 渲染接口: POST /api/render

### 前端
```bash
cd frontend
npm install
npm run dev
```

前端默认监听 http://localhost:5173，已配置 /api 代理到后端 8000 端口。

### 运行测试
```bash
# 后端测试（在项目根目录执行）
pytest

# 前端测试
cd frontend && npx vitest run
```

​4. 关键逻辑约束 (Logic Rules)
​为了确保生成的图像不像“机器人”，在编写生成模块时必须遵循：
​基线偏移 (Baseline Drift): 每一行的文字不能在绝对水平线上，需有 \pm 2 像素的随机上下浮动。
​字距随机 (Kerning Jitter): 字符间的间距不能固定，需有微小的随机缩进。
​模拟涂改 (Erasure/Scratch Marks): 随机在文稿中插入“划掉重写”的笔触轨迹。
​墨迹深浅: 模拟压力感，笔触颜色在 rgb(30, 30, 30) 到 rgb(60, 60, 60) 之间波动。
​5. 代码规范 (Coding Standards)
​Python: 遵循 PEP8，使用 Type Hints 增强可读性。
​Vue: 必须使用 <script setup> 语法，组件库保持轻量。
​测试优先: 在实现任何功能函数前，必须先在 tests/ 目录下创建对应的测试用力。
​6. 项目结构 (Project Structure)
/
├── requirements.txt           # Python 依赖
├── CLAUDE.md
├── backend/
│   ├── __init__.py
│   ├── app.py                 # FastAPI 入口（健康检查 + 渲染接口）
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── layout.py          # 文本布局：换行、基线偏移、字距抖动
│   │   ├── effects.py         # 视觉效果：涂改痕迹、墨迹深浅
│   │   └── renderer.py        # 渲染编排引擎
│   ├── fonts/                 # 存放手写字体 .ttf 文件
│   └── tests/
│       ├── test_layout.py
│       ├── test_effects.py
│       └── test_renderer.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js         # Vite 配置（含 /api 代理）
│   ├── index.html
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── assets/main.css
│   │   └── components/
│   │       ├── Editor.vue     # 文本编辑 + 参数调节
│   │       └── Preview.vue    # 预览 + 下载（三态处理）
│   └── tests/
│       └── example.test.js
