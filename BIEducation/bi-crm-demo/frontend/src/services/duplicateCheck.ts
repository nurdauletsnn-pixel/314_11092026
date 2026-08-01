import { apiClient } from '../api/client'

export interface DuplicateCheckResult {
  exists: boolean
  contact: {
    id: string
    full_name: string
    phone: string
    iin?: string
    email?: string
  } | null
  branch: {
    id: string
    name: string
    code?: string
    city?: string
  } | null
}

/**
 * Анти-дубль по ИИН / Телефону (раздел 7, Риск 4).
 * Вызывает /api/contacts/check-duplicate/?phone=...&iin=...
 * Бэкенд ищет по всей БД (не только по филиалу пользователя) и возвращает
 * branch, чтобы показать плашку «Контакт найден в филиале X».
 */
export async function checkDuplicateContact(phone?: string, iin?: string): Promise<DuplicateCheckResult> {
  const params: Record<string, string> = {}
  if (phone) params.phone = phone
  if (iin) params.iin = iin

  if (!phone && !iin) {
    return { exists: false, contact: null, branch: null }
  }

  const response = await apiClient.get('/contacts/check-duplicate/', { params })
  return response.data as DuplicateCheckResult
}