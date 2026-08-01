interface DuplicateContactBannerProps {
  match: {
    id: string
    fullName: string
    phone: string
    iin?: string
    branchName?: string
    isCrossBranch: boolean
  }
  attachToExisting: boolean
  onAttach: () => void
}

/**
 * Плашка анти-дубля (раздел 7, Риск 4 / раздел 8.2 «Merge дублей»).
 * Показывает «Контакт найден в филиале X» и предлагает привязать новую сделку
 * к существующей карточке родителя вместо создания нового Contact.
 */
export function DuplicateContactBanner({ match, attachToExisting, onAttach }: DuplicateContactBannerProps) {
  const isOwnBranch = !match.isCrossBranch

  return (
    <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <p className="text-sm font-semibold text-sky-900">🔍 Контакт уже существует в системе</p>
          <p className="mt-1 text-sm text-sky-800">
            {match.fullName} • {match.phone}
            {match.iin ? ` • ИИН ${match.iin}` : ''}
          </p>
          {match.isCrossBranch ? (
            <p className="mt-1 text-sm font-medium text-amber-700">
              ⚠️ Контакт найден в филиале {match.branchName ?? 'другом филиале'}.
              {' '}Новая сделка будет привязана к существующей карточке родителя, дубликат не создаётся.
            </p>
          ) : (
            <p className="mt-1 text-sm text-sky-700">
              Контакт найден в вашем филиале ({match.branchName}). Привяжем новую сделку к нему.
            </p>
          )}
        </div>
        <div className="shrink-0">
          {attachToExisting ? (
            <span className="rounded-full bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white">
              ✓ Будет привязан
            </span>
          ) : (
            <button
              onClick={onAttach}
              className="rounded-full bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-700"
            >
              Привязать к существующему контакту
            </button>
          )}
        </div>
      </div>
      {isOwnBranch && !attachToExisting && (
        <p className="mt-2 text-xs text-sky-600">
          Подсказка: если вы создадите новую сделку, система не создаст дубликат — используется существующий Contact.
        </p>
      )}
    </div>
  )
}

export default DuplicateContactBanner