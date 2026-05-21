<script setup>
import { ref, nextTick, watch } from 'vue'

const emit = defineEmits(['update:background'])

const fileInput = ref(null)
const previewUrl = ref(null)
const imgRef = ref(null)
const canvasRef = ref(null)
const hasImage = ref(false)
const dragging = ref(-1)

// 归一化坐标 (0~1)，默认居中 80%
const points = ref([
  [0.1, 0.1],
  [0.9, 0.1],
  [0.9, 0.9],
  [0.1, 0.9],
])

// ---------- 图片压缩 ----------

function compressImage(file, maxWidth = 2000) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        let { width, height } = img
        if (width > maxWidth) {
          height = Math.round(height * maxWidth / width)
          width = maxWidth
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, width, height)
        canvas.toBlob(resolve, 'image/jpeg', 0.9)
      }
      img.src = e.target.result
    }
    reader.readAsDataURL(file)
  })
}

// ---------- 画布绘制 ----------

const colors = ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b']

function drawCanvas() {
  const canvas = canvasRef.value
  const img = imgRef.value
  if (!canvas || !img) return

  const rect = img.getBoundingClientRect()
  canvas.width = rect.width
  canvas.height = rect.height
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // 四点屏幕坐标
  const pts = points.value.map(p => [p[0] * canvas.width, p[1] * canvas.height])

  // 连线
  ctx.strokeStyle = 'rgba(59, 130, 246, 0.5)'
  ctx.lineWidth = 2
  ctx.setLineDash([6, 4])
  ctx.beginPath()
  ctx.moveTo(pts[0][0], pts[0][1])
  for (let i = 1; i < 4; i++) ctx.lineTo(pts[i][0], pts[i][1])
  ctx.closePath()
  ctx.stroke()
  ctx.setLineDash([])

  // 四个拖拽点
  for (let i = 0; i < 4; i++) {
    const [cx, cy] = pts[i]

    // 外发光
    ctx.beginPath()
    ctx.arc(cx, cy, 12, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(255,255,255,0.3)'
    ctx.fill()

    // 圆点
    ctx.beginPath()
    ctx.arc(cx, cy, 8, 0, Math.PI * 2)
    ctx.fillStyle = colors[i]
    ctx.fill()
    ctx.strokeStyle = 'white'
    ctx.lineWidth = 2.5
    ctx.stroke()

    // 编号
    ctx.fillStyle = 'white'
    ctx.font = 'bold 11px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(i + 1, cx, cy)
  }
}

// ---------- 鼠标事件 ----------

function getCanvasPos(e) {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  return { x: e.clientX - rect.left, y: e.clientY - rect.top }
}

function onMouseDown(e) {
  const canvas = canvasRef.value
  const { x, y } = getCanvasPos(e)
  for (let i = 0; i < 4; i++) {
    const px = points.value[i][0] * canvas.width
    const py = points.value[i][1] * canvas.height
    if (Math.hypot(x - px, y - py) < 18) {
      dragging.value = i
      return
    }
  }
}

function onMouseMove(e) {
  if (dragging.value < 0) return
  const canvas = canvasRef.value
  const { x, y } = getCanvasPos(e)
  points.value[dragging.value] = [
    Math.max(0, Math.min(1, x / canvas.width)),
    Math.max(0, Math.min(1, y / canvas.height)),
  ]
  drawCanvas()
}

function onMouseUp() {
  if (dragging.value >= 0) {
    dragging.value = -1
    emitChange()
  }
}

function onMouseLeave() { onMouseUp() }

// ---------- 文件上传 ----------

function emitChange() {
  // 拖拽点结束时通知父组件更新坐标
  notifyParent()
}

const naturalSize = ref({ width: 0, height: 0 })
const currentBlob = ref(null)

async function handleFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const compressed = await compressImage(file)
  currentBlob.value = compressed

  // 获取压缩后图片的原始尺寸
  const img = new Image()
  img.onload = () => {
    naturalSize.value = { width: img.naturalWidth, height: img.naturalHeight }
    URL.revokeObjectURL(img.src)
    // naturalSize 就绪后才能通知父组件，否则坐标乘以 0 全变 [0,0]
    notifyParent()
  }
  img.src = URL.createObjectURL(compressed)

  previewUrl.value = URL.createObjectURL(compressed)
  hasImage.value = true
  await nextTick()
  drawCanvas()
  // 注意：notifyParent 已移到 img.onload 内部，这里不能调！
}

function notifyParent() {
  if (!previewUrl.value) return
  emit('update:background', {
    blob: currentBlob.value,
    points: points.value.map(p => [...p]),
    naturalWidth: naturalSize.value.width,
    naturalHeight: naturalSize.value.height,
  })
}

function removeImage() {
  previewUrl.value = null
  hasImage.value = false
  points.value = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
  emit('update:background', null)
}

// 重置坐标为默认
function resetPoints() {
  points.value = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
  nextTick(() => { drawCanvas(); notifyParent() })
}

watch(points, () => { nextTick(drawCanvas) }, { deep: true })
</script>

<template>
  <div class="mb-4">
    <label class="block text-sm text-gray-600 mb-2">背景图片</label>

    <!-- 未上传：显示上传按钮 -->
    <div v-if="!hasImage">
      <button
        @click="fileInput?.click()"
        class="w-full py-8 border-2 border-dashed border-gray-300 rounded-lg text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors text-sm"
      >
        + 点击上传背景图片
      </button>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="handleFile"
      />
    </div>

    <!-- 已上传：缩略图 + 四点拾取器 -->
    <div v-else class="relative">
      <div class="relative inline-block w-full">
        <img
          ref="imgRef"
          :src="previewUrl"
          class="w-full rounded-lg border border-gray-200"
          alt="背景预览"
          @load="drawCanvas"
        />
        <canvas
          ref="canvasRef"
          class="absolute inset-0 w-full h-full cursor-crosshair rounded-lg"
          @mousedown="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseLeave"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="flex gap-2 mt-2">
        <button
          @click="fileInput?.click()"
          class="text-xs px-3 py-1 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
        >
          更换图片
        </button>
        <button
          @click="resetPoints"
          class="text-xs px-3 py-1 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
        >
          重置选区
        </button>
        <button
          @click="removeImage"
          class="text-xs px-3 py-1 bg-red-50 text-red-500 rounded hover:bg-red-100 transition-colors"
        >
          移除
        </button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="handleFile"
      />
      <p class="text-xs text-gray-400 mt-1">拖动四个彩色圆点调整透视对齐区域</p>
    </div>
  </div>
</template>
