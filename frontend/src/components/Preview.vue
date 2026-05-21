<script setup>
defineProps({
  imageUrl: { type: String, default: null },
  isLoading: { type: Boolean, default: false },
  error: { type: String, default: null },
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold text-gray-700 mb-4">预览</h2>

    <!-- 加载态 -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center h-64 text-gray-400"
    >
      <div class="text-center">
        <svg class="animate-spin h-8 w-8 mx-auto mb-2" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span>正在生成手写图像...</span>
      </div>
    </div>

    <!-- 错误态 -->
    <div
      v-else-if="error"
      class="flex items-center justify-center h-64 text-red-500 bg-red-50 rounded-md"
    >
      <div class="text-center">
        <p class="font-medium">生成失败</p>
        <p class="text-sm mt-1">{{ error }}</p>
      </div>
    </div>

    <!-- 空态 -->
    <div
      v-else-if="!imageUrl"
      class="flex items-center justify-center h-64 text-gray-400 bg-gray-50 rounded-md border-2 border-dashed border-gray-200"
    >
      <div class="text-center">
        <p class="text-4xl mb-2">&#9998;</p>
        <p class="text-sm">在左侧输入文本，点击生成预览</p>
      </div>
    </div>

    <!-- 图像预览 -->
    <div v-else class="flex flex-col items-center">
      <img
        :src="imageUrl"
        alt="手写预览"
        class="max-w-full rounded-md shadow-sm border border-gray-200"
      />
      <a
        :href="imageUrl"
        download="handwriting.png"
        class="mt-4 py-2 px-6 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors text-sm"
      >
        下载 PNG
      </a>
    </div>
  </div>
</template>
