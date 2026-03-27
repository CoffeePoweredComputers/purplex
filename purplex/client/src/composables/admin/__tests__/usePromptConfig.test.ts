import { beforeEach, describe, expect, it } from 'vitest'
import { type PromptConfig, usePromptConfig } from '../usePromptConfig'

describe('usePromptConfig', () => {
  let prompt: ReturnType<typeof usePromptConfig>

  beforeEach(() => {
    prompt = usePromptConfig()
  })

  describe('initial state', () => {
    it('should initialize with empty values', () => {
      expect(prompt.imageUrl.value).toBe('')
      expect(prompt.altText.value).toBe('')
      expect(prompt.hasImage.value).toBe(false)
    })

    it('should consider empty URL as valid', () => {
      expect(prompt.isValidUrl.value).toBe(true)
    })
  })

  describe('loadConfig', () => {
    it('should load config with image URL', () => {
      const config: PromptConfig = {
        image_url: 'https://example.com/image.png',
        image_alt_text: 'A test image',
      }

      prompt.loadConfig(config)

      expect(prompt.imageUrl.value).toBe('https://example.com/image.png')
      expect(prompt.altText.value).toBe('A test image')
      expect(prompt.hasImage.value).toBe(true)
    })

    it('should handle null config gracefully', () => {
      // First set some values
      prompt.setImageUrl('https://example.com/image.png')
      prompt.setAltText('Alt text')

      // Then load null config
      prompt.loadConfig(null)

      expect(prompt.imageUrl.value).toBe('')
      expect(prompt.altText.value).toBe('')
    })

    it('should handle undefined config gracefully', () => {
      prompt.setImageUrl('https://example.com/image.png')
      prompt.loadConfig(undefined)

      expect(prompt.imageUrl.value).toBe('')
      expect(prompt.altText.value).toBe('')
    })

    it('should handle config with missing fields', () => {
      const config = {
        image_url: 'https://example.com/image.png',
        // image_alt_text is missing
      } as PromptConfig

      prompt.loadConfig(config)

      expect(prompt.imageUrl.value).toBe('https://example.com/image.png')
      expect(prompt.altText.value).toBe('')
    })
  })

  describe('URL validation', () => {
    it('should validate correct URLs', () => {
      prompt.setImageUrl('https://example.com/image.png')
      expect(prompt.isValidUrl.value).toBe(true)

      prompt.setImageUrl('http://localhost:8000/media/test.jpg')
      expect(prompt.isValidUrl.value).toBe(true)

      prompt.setImageUrl('https://cdn.example.com/path/to/image.webp')
      expect(prompt.isValidUrl.value).toBe(true)
    })

    it('should reject invalid URLs', () => {
      prompt.setImageUrl('not-a-url')
      expect(prompt.isValidUrl.value).toBe(false)

      prompt.setImageUrl('example.com/image.png')
      expect(prompt.isValidUrl.value).toBe(false)

      prompt.setImageUrl('//example.com/image.png')
      expect(prompt.isValidUrl.value).toBe(false)
    })

    it('should consider empty URL as valid', () => {
      prompt.setImageUrl('')
      expect(prompt.isValidUrl.value).toBe(true)

      prompt.setImageUrl('   ')
      expect(prompt.isValidUrl.value).toBe(true)
    })
  })

  describe('getConfigForApi', () => {
    it('should trim whitespace on save', () => {
      prompt.setImageUrl('  https://example.com/image.png  ')
      prompt.setAltText('  A test image  ')

      const config = prompt.getConfigForApi()

      expect(config.image_url).toBe('https://example.com/image.png')
      expect(config.image_alt_text).toBe('A test image')
    })

    it('should return empty strings when no values set', () => {
      const config = prompt.getConfigForApi()

      expect(config.image_url).toBe('')
      expect(config.image_alt_text).toBe('')
    })
  })

  describe('setters', () => {
    it('should set image URL', () => {
      prompt.setImageUrl('https://example.com/new.png')
      expect(prompt.imageUrl.value).toBe('https://example.com/new.png')
    })

    it('should set alt text', () => {
      prompt.setAltText('New alt text')
      expect(prompt.altText.value).toBe('New alt text')
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      prompt.setImageUrl('https://example.com/image.png')
      prompt.setAltText('Alt text')

      prompt.reset()

      expect(prompt.imageUrl.value).toBe('')
      expect(prompt.altText.value).toBe('')
      expect(prompt.hasImage.value).toBe(false)
    })
  })
})
