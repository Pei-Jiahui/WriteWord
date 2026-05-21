<script setup>
import { ref, reactive, onMounted } from 'vue'
import BackgroundUploader from './BackgroundUploader.vue'

const emit = defineEmits(['render'])
defineProps({
  isLoading: { type: Boolean, default: false },
})

const text = ref('')
const fonts = ref([])
const selectedFont = ref('')
const fontsLoading = ref(true)
const backgroundData = ref(null)

const options = reactive({
  fontSize: 32,
  lineSpacing: 1.8,
  letterSpacing: 0,
  imageWidth: 800,
  imageHeight: 600,
  baselineDrift: 2,
  kerningJitter: 1,
  errorRate: 0.05,
  inkVariation: 15,
  spacingRandomness: 2,
})

onMounted(async () => {
  try {
    const resp = await fetch('/api/fonts')
    const list = await resp.json()
    fonts.value = list.map(f => ({ ...f, loaded: false }))
    if (fonts.value.length > 0) {
      selectedFont.value = fonts.value[0].name
    }
    await Promise.allSettled(fonts.value.map(async (font) => {
      try {
        const url = `/fonts/${encodeURIComponent(font.file)}`
        const ff = new FontFace(font.name, `url(${url})`)
        await ff.load()
        document.fonts.add(ff)
        font.loaded = true
      } catch (e) {
        console.warn(`字体 "${font.name}" 加载失败`, e)
      }
    }))
  } catch (e) {
    console.error('获取字体列表失败', e)
  } finally {
    fontsLoading.value = false
  }
})

function setFont(name) {
  selectedFont.value = name
}

function onBackgroundChange(data) {
  backgroundData.value = data
}

function onSubmit() {
  if (!text.value.trim()) return
  emit('render', text.value, { ...options, fontName: selectedFont.value }, backgroundData.value)
}
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold text-gray-700 mb-4">文本编辑</h2>

    <!-- 背景上传 -->
    <BackgroundUploader @update:background="onBackgroundChange" />

    <!-- 字体选择 -->
    <div class="mb-4">
      <label class="block text-sm text-gray-600 mb-2">选择字体</label>
      <div v-if="fontsLoading" class="text-sm text-gray-400 py-2">字体加载中...</div>
      <div v-else class="flex gap-2 overflow-x-auto pb-2">
        <button
          v-for="font in fonts"
          :key="font.name"
          @click="setFont(font.name)"
          :class="[
            'flex-shrink-0 w-28 py-3 rounded-lg border-2 text-sm transition-colors',
            selectedFont === font.name
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
          ]"
        >
          <span
            class="block truncate"
            :style="{ fontFamily: font.loaded ? `'${font.name}', serif` : 'serif', fontSize: '16px' }"
          >
            {{ font.name }}
          </span>
          <span
            class="block text-sm mt-1 opacity-60"
            :style="{ fontFamily: font.loaded ? `'${font.name}', serif` : 'serif' }"
          >
            弓长张
          </span>
        </button>
      </div>
    </div>

    <div class="mb-4">
      <label class="block text-sm text-gray-600 mb-1">输入文本</label>
      <textarea
        v-model="text"
        placeholder="在此输入要转换为手写的文本..."
        rows="6"
        class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
      ></textarea>
    </div>

    <div class="space-y-3">
      <div>
        <label class="block text-sm text-gray-600">字号：{{ options.fontSize }}px</label>
        <input type="range" v-model.number="options.fontSize" min="12" max="100" class="w-full" />
      </div>

      <div>
        <label class="block text-sm text-gray-600">行间距：{{ options.lineSpacing.toFixed(1) }}</label>
        <input type="range" v-model.number="options.lineSpacing" min="-1.0" max="3.0" step="0.1" class="w-full" />
      </div>

      <div>
        <label class="block text-sm text-gray-600">字间距：{{ options.letterSpacing }}px</label>
        <input type="range" v-model.number="options.letterSpacing" min="-10" max="20" step="1" class="w-full" />
      </div>

      <div>
        <label class="block text-sm text-gray-600">错误触发率：{{ (options.errorRate * 100).toFixed(0) }}%</label>
        <input type="range" v-model.number="options.errorRate" min="0" max="1.0" step="0.01" class="w-full" />
      </div>

      <div>
        <label class="block text-sm text-gray-600">排版随机度：{{ options.spacingRandomness.toFixed(1) }}</label>
        <input type="range" v-model.number="options.spacingRandomness" min="0" max="6" step="0.5" class="w-full" />
      </div>
    </div>

    <button
      @click="onSubmit"
      :disabled="isLoading || !text.trim()"
      class="mt-6 w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {{ isLoading
        ? (backgroundData ? '合成中...' : '生成中...')
        : (backgroundData ? '合成到手写背景' : '生成手写图像')
      }}
    </button>
  </div>
</template>
