/// <reference types="vite/client" />

interface SaveFilePickerOptions {
  suggestedName?: string
  types?: Array<{
    description?: string
    accept: Record<string, string[]>
  }>
}

interface FileSystemWritableFileStream extends WritableStream {
  write(data: BufferSource | Blob | string): Promise<void>
  close(): Promise<void>
}

interface FileSystemFileHandle {
  readonly name: string
  createWritable(): Promise<FileSystemWritableFileStream>
}

interface Window {
  showSaveFilePicker?: (options?: SaveFilePickerOptions) => Promise<FileSystemFileHandle>
}
