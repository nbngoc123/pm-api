import { ApiError } from '@/api/client'

export interface FormErrors {
  form?: string
  message?: string
  fields: Record<string, string>
}

export function toFormErrors(err: unknown): FormErrors {
  const fields: Record<string, string> = {}
  let form: string | undefined = undefined

  if (err instanceof ApiError) {
    form = err.message
    if (err.details && Array.isArray(err.details)) {
      for (const item of err.details) {
        if (item.field && item.message) {
          fields[item.field] = item.message
        }
      }
    }
  } else if (err instanceof Error) {
    form = err.message
  }

  return { form, message: form, fields }
}
