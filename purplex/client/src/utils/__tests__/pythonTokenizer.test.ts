import { beforeEach, describe, expect, it, vi } from 'vitest'

// Mock ace-builds with a fake Python tokenizer
const mockGetLineTokens = vi.fn()

vi.mock('ace-builds', () => ({
  default: {
    require: vi.fn(() => ({
      Mode: vi.fn().mockImplementation(() => ({
        getTokenizer: () => ({
          getLineTokens: mockGetLineTokens
        })
      }))
    }))
  }
}))

vi.mock('ace-builds/src-noconflict/mode-python', () => ({}))

import { tokenizePython } from '../pythonTokenizer'

describe('tokenizePython', () => {
  beforeEach(() => {
    mockGetLineTokens.mockReset()
  })

  it('tokenizes a simple function definition', () => {
    mockGetLineTokens
      .mockReturnValueOnce({
        tokens: [
          { type: 'keyword', value: 'def' },
          { type: 'text', value: ' ' },
          { type: 'identifier', value: 'foo' },
          { type: 'paren.lparen', value: '(' },
          { type: 'paren.rparen', value: ')' },
          { type: 'punctuation', value: ':' }
        ],
        state: 'start'
      })
      .mockReturnValueOnce({
        tokens: [
          { type: 'text', value: '  ' },
          { type: 'keyword', value: 'return' },
          { type: 'text', value: ' ' },
          { type: 'constant.numeric', value: '42' }
        ],
        state: 'start'
      })

    const result = tokenizePython('def foo():\n  return 42')

    expect(result).toHaveLength(2)
    expect(result[0][0]).toEqual({ type: 'keyword', value: 'def' })
    expect(result[1][1]).toEqual({ type: 'keyword', value: 'return' })
    expect(result[1][3]).toEqual({ type: 'constant.numeric', value: '42' })
  })

  it('returns one line with empty tokens for empty input', () => {
    mockGetLineTokens.mockReturnValueOnce({
      tokens: [],
      state: 'start'
    })

    const result = tokenizePython('')
    expect(result).toHaveLength(1)
    expect(result[0]).toHaveLength(0)
  })

  it('threads state across lines for multiline strings', () => {
    mockGetLineTokens
      .mockReturnValueOnce({
        tokens: [{ type: 'string', value: '"""hello' }],
        state: 'qqstring3'
      })
      .mockReturnValueOnce({
        tokens: [{ type: 'string', value: 'world"""' }],
        state: 'start'
      })

    const result = tokenizePython('"""hello\nworld"""')

    expect(result).toHaveLength(2)
    expect(result[0][0].type).toBe('string')
    expect(result[1][0].type).toBe('string')

    // Verify state was threaded: second call should receive 'qqstring3'
    expect(mockGetLineTokens).toHaveBeenNthCalledWith(2, 'world"""', 'qqstring3')
  })

  it('handles empty lines in the middle', () => {
    mockGetLineTokens
      .mockReturnValueOnce({
        tokens: [{ type: 'keyword', value: 'pass' }],
        state: 'start'
      })
      .mockReturnValueOnce({
        tokens: [],
        state: 'start'
      })
      .mockReturnValueOnce({
        tokens: [{ type: 'keyword', value: 'pass' }],
        state: 'start'
      })

    const result = tokenizePython('pass\n\npass')

    expect(result).toHaveLength(3)
    expect(result[1]).toHaveLength(0)
  })
})
