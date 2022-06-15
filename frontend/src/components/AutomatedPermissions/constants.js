export const TIME_PER_INTERVAL = 1000 * 10

export const APPLIED_POLICY_STATUSES = [
  'applied_awaiting_execution',
  'applied_and_success',
  'applied_and_failure',
  'approved',
]

export const editorOptions = {
  selectOnLineNumbers: true,
  quickSuggestions: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false,
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  wordWrap: 'wordWrapColumn',
  wordWrapColumn: 120,
}
