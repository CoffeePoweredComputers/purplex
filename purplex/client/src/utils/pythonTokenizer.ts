import ace from 'ace-builds'
import 'ace-builds/src-noconflict/mode-python'

export interface SyntaxToken {
  type: string
  value: string
}

export type TokenizedLine = SyntaxToken[]

/**
 * Tokenize Python source code using Ace's Python mode tokenizer.
 * State is threaded line-by-line so multiline strings tokenize correctly.
 */
export function tokenizePython(code: string): TokenizedLine[] {
  const PythonMode = ace.require('ace/mode/python').Mode
  const tokenizer = new PythonMode().getTokenizer()
  const lines = code.split('\n')
  const result: TokenizedLine[] = []
  let state: string | string[] = 'start'

  for (const line of lines) {
    const lineResult = tokenizer.getLineTokens(line, state)
    result.push(lineResult.tokens)
    state = lineResult.state
  }

  return result
}
