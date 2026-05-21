<script setup>
import { ref } from 'vue'
import axios from 'axios'
import Editor from './components/Editor.vue'
import Preview from './components/Preview.vue'

const imageUrl = ref(null)
const isLoading = ref(false)
const error = ref(null)

async function handleRender(text, options, backgroundData) {
  isLoading.value = true
  error.value = null
  imageUrl.value = null

  try {
    if (backgroundData) {
      // ---- 自定义背景渲染 (axios multipart) ----
      const formData = new FormData()
      formData.append('file', backgroundData.blob, 'background.jpg')
      formData.append('text', text)
      formData.append('font_name', options.fontName || '')
      formData.append('font_size', String(options.fontSize))
      formData.append('letter_spacing', String(options.letterSpacing))
      formData.append('line_spacing', String(options.lineSpacing))
      formData.append('baseline_drift', String(options.baselineDrift))
      formData.append('ink_variation', String(options.inkVariation))
      formData.append('error_rate', String(options.errorRate))
      formData.append('kerning_jitter', String(options.kerningJitter))
      formData.append('spacing_randomness', String(options.spacingRandomness))

      const pts = backgroundData.points.map(p => [
        Math.round(p[0] * backgroundData.naturalWidth),
        Math.round(p[1] * backgroundData.naturalHeight),
      ])
      formData.append('dst_points', JSON.stringify(pts))

      const axResp = await axios.post('/api/render/custom', formData, {
        responseType: 'blob',
      })
      imageUrl.value = URL.createObjectURL(axResp.data)
    } else {
      // ---- 普通渲染 (JSON) ----
      resp = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          font_name: options.fontName || '',
          font_size: options.fontSize,
          letter_spacing: options.letterSpacing,
          line_spacing: options.lineSpacing,
          image_width: options.imageWidth,
          image_height: options.imageHeight,
          baseline_drift: options.baselineDrift,
          kerning_jitter: options.kerningJitter,
          error_rate: options.errorRate,
          ink_variation: options.inkVariation,
        }),
      })

      if (!resp.ok) {
        const detail = await resp.json()
        throw new Error(detail.detail || '渲染失败')
      }

      const resultBlob = await resp.blob()
      imageUrl.value = URL.createObjectURL(resultBlob)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <header class="mb-8 text-center">
      <h1 class="text-3xl font-bold text-gray-800">WriteWords</h1>
      <p class="text-gray-500 mt-1">将电子文本转换为模拟手写图像</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <Editor :is-loading="isLoading" @render="handleRender" />
      <Preview :image-url="imageUrl" :is-loading="isLoading" :error="error" />
    </div>
  </div>
</template>
