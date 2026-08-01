import { useEffect, useRef, useState } from 'react'
import { Briefcase, CalendarDays, CreditCard, User, X } from 'lucide-react'
import type { Deal, CurrentUser, PaymentScheduleEntry, PipelineId } from '../types'
import { mockBranches, mockTariffs } from '../data/mockData'
import { apiClient } from '../api/client'
import {
  canDeleteDeal,
  canEditPricing,
  canMarkPaymentPaid,
} from '../services/accessControl'
import { checkDuplicateContact } from '../services/duplicateCheck'
import DuplicateContactBanner from './DuplicateContactBanner'
import PaymentScheduleList from './PaymentScheduleList'

interface DealModalProps {
  deal: Deal | null
  mode?: 'edit' | 'create'
  currentUser?: CurrentUser | null
  fixedBranchId?: string | null
  /** Текущая выбранная воронка — определяет тип анкеты при создании (B2B vs B2C). */
  pipelineId?: PipelineId
  onClose: () => void
  onSaveDeal?: (payload: Partial<Deal> & { id?: string }) => void
  onCreateDeal?: (payload: Partial<Deal>) => void
  onDeleteDeal?: (dealId: string) => void
}

interface DuplicateMatch {
  id: string
  fullName: string
  phone: string
  iin?: string
  branchName?: string
  isCrossBranch: boolean
}

type ModalTab = 'people' | 'tariff' | 'schedule'

interface ServerPreview {
  total_amount: string
  entrance_fee: string
  schedules: Array<{ title: string; amount: string; due_date: string; status: string }>
}

export function DealModal({
  deal,
  mode = 'edit',
  currentUser,
  fixedBranchId,
  pipelineId,
  onClose,
  onSaveDeal,
  onCreateDeal,
  onDeleteDeal,
}: DealModalProps) {
  const isCreateMode = mode === 'create'
  // B2B-анкета показывается ТОЛЬКО:
  //  — при создании, если выбрана вкладка B2B (pipelineId === 'b2b');
  //  — при редактировании существующей B2B-сделки.
  const isB2BMode = isCreateMode
    ? pipelineId === 'b2b'
    : (deal?.pipelineId === 'b2b' || Boolean(deal?.b2b) || Boolean(deal?.partnerType))
  const [activeTab, setActiveTab] = useState<ModalTab>('people')

  // --- Родитель и ребёнок (B2C) ---
  const [parentName, setParentName] = useState(deal?.parent.name ?? '')
  const [parentPhone, setParentPhone] = useState(deal?.parent.phone ?? '')
  const [parentIin, setParentIin] = useState(deal?.parent.iin ?? '')
  const [childName, setChildName] = useState(deal?.child.name ?? '')
  const [gradeOrGroup, setGradeOrGroup] = useState(deal?.child.gradeOrGroup ?? '')

  // --- B2B: Заказчик и Проект ---
  const [b2bCompany, setB2bCompany] = useState(deal?.b2b?.companyName ?? '')
  const [b2bBin, setB2bBin] = useState(deal?.b2b?.bin ?? '')
  const [b2bContactPerson, setB2bContactPerson] = useState(deal?.b2b?.contactPerson ?? '')
  const [b2bPosition, setB2bPosition] = useState(deal?.b2b?.position ?? '')
  const [b2bPhone, setB2bPhone] = useState(deal?.b2b?.phone ?? '')
  const [b2bEmail, setB2bEmail] = useState(deal?.b2b?.email ?? '')
  const [b2bServiceType, setB2bServiceType] = useState(deal?.b2b?.serviceType ?? 'Франчайзинг')
  const [b2bBudget, setB2bBudget] = useState<string>(
    deal?.b2b?.budget ? String(deal.b2b.budget) : deal?.contractValue ? String(deal.contractValue) : ''
  )

  // --- Тариф и доп. услуги ---
  const [branchId, setBranchId] = useState(deal?.branchId ?? fixedBranchId ?? mockBranches[0].id)
  const [sourceCity, setSourceCity] = useState(deal?.sourceCity ?? mockBranches.find((b) => b.id === branchId)?.city ?? '')
  const [sourceBranchRequested, setSourceBranchRequested] = useState(deal?.sourceBranchRequested ?? mockBranches.find((b) => b.id === branchId)?.code ?? '')
  const [tariffId, setTariffId] = useState(deal?.tariffId ?? '')
  const [hasFood, setHasFood] = useState(deal?.hasFood ?? false)
  const [hasTransport, setHasTransport] = useState(deal?.hasTransport ?? false)
  const [transportZone, setTransportZone] = useState<'CITY' | 'SUBURB'>('CITY')
  const [isSecondChild, setIsSecondChild] = useState(deal?.child?.isSecondChild ?? false)
  const [isWaitlisted, setIsWaitlisted] = useState(deal?.isWaitlisted ?? false)

  // --- График платежей ---
  const [paymentSchedule, setPaymentSchedule] = useState<PaymentScheduleEntry[] | undefined>(deal?.paymentSchedule)

  // --- Серверный превью-расчёт ---
  const [serverPreview, setServerPreview] = useState<ServerPreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // --- Анти-дубль (раздел 7, Риск 4) ---
  const [duplicateMatch, setDuplicateMatch] = useState<DuplicateMatch | null>(null)
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false)
  const [attachToExisting, setAttachToExisting] = useState(false)
  const debounceRef = useRef<number | null>(null)

  const availableTariffs = mockTariffs.filter((t) => {
    const branch = mockBranches.find((b) => b.id === branchId)
    return branch ? t.branchCode === branch.code : true
  })

  const selectedTariff = mockTariffs.find((t) => t.id === tariffId) ?? availableTariffs[0]

  // RBAC: редактирование тарифов/прайса — только HQ_ADMIN (раздел 8.2).
  const pricingLocked = !canEditPricing(currentUser ?? null)

  const isAldiBranch = mockBranches.find((b) => b.id === branchId)?.code?.startsWith('ALDI_BI') ?? false

  // Кросс-филиальный лид (раздел 8.5)
  const requestedBranch = mockBranches.find((b) => b.code === sourceBranchRequested)
  const isCrossBranchLead = Boolean(
    isCreateMode && requestedBranch && requestedBranch.code !== mockBranches.find((b) => b.id === branchId)?.code
  )

  // Серверный калькулятор: GET /api/tariffs/calculate/
  useEffect(() => {
    if (isB2BMode) return
    if (!selectedTariff || !branchId) return
    const branchCode = mockBranches.find((b) => b.id === branchId)?.code
    if (!branchCode) return

    setPreviewError(null)
    setServerPreview(null)

    apiClient
      .get('/tariffs/calculate/', {
        params: {
          branch: branchCode,
          tariff: selectedTariff.name,
          has_food: hasFood,
          has_transport: hasTransport,
          transport_zone: transportZone,
          is_second_child: isSecondChild,
        },
      })
      .then((response) => setServerPreview(response.data))
      .catch((err) => {
        const msg = err?.response?.data?.error || 'Не удалось рассчитать тариф'
        setPreviewError(msg)
      })
  }, [selectedTariff, branchId, hasFood, hasTransport, transportZone, isSecondChild, isB2BMode])

  // Проверка дублей при вводе телефона/ИИН (дебаунс 300ms)
  useEffect(() => {
    if (!isCreateMode || isB2BMode) return
    if (debounceRef.current) window.clearTimeout(debounceRef.current)

    const phone = parentPhone.trim()
    const iin = parentIin.trim()
    if (!phone && !iin) {
      setDuplicateMatch(null)
      setAttachToExisting(false)
      return
    }

    debounceRef.current = window.setTimeout(async () => {
      setIsCheckingDuplicate(true)
      try {
        const result = await checkDuplicateContact(phone || undefined, iin || undefined)
        if (result.exists && result.contact) {
          const isCrossBranch = result.branch?.id !== branchId
          setDuplicateMatch({
            id: result.contact.id,
            fullName: result.contact.full_name,
            phone: result.contact.phone,
            iin: result.contact.iin,
            branchName: result.branch?.name,
            isCrossBranch,
          })
          if (attachToExisting) {
            setParentName(result.contact.full_name)
            setParentPhone(result.contact.phone)
            if (result.contact.iin) setParentIin(result.contact.iin)
          }
        } else {
          setDuplicateMatch(null)
        }
      } catch {
        setDuplicateMatch(null)
      } finally {
        setIsCheckingDuplicate(false)
      }
    }, 300)

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [parentPhone, parentIin, isCreateMode, branchId, attachToExisting, isB2BMode])

  const handleMarkPaid = (scheduleId: string) => {
    // В демо — локально обновляем статус. Реальный API: POST /payment-schedules/{id}/mark-paid/
    setPaymentSchedule((prev) =>
      prev?.map((item) => (item.id === scheduleId ? { ...item, status: 'PAID' as const } : item))
    )
  }

  const handleSave = () => {
    const b2bBudgetNum = Number(b2bBudget)
    const payload: Partial<Deal> & { id?: string } = {
      id: deal?.id,
      // Воронка: при создании — из пропа (текущая вкладка), при редактировании — из сделки.
      pipelineId: isB2BMode ? ('b2b' as PipelineId) : ((deal?.pipelineId ?? pipelineId ?? 'school') as PipelineId),
      parent: isB2BMode
        ? { id: deal?.parent.id ?? `p${Date.now()}`, name: b2bCompany || 'B2B-клиент', phone: b2bPhone, iin: b2bBin || undefined, email: b2bEmail || undefined }
        : { id: deal?.parent.id ?? `p${Date.now()}`, name: parentName, phone: parentPhone, iin: parentIin || undefined },
      child: isB2BMode
        ? deal?.child ?? { id: 'b2b-no-child', parentId: 'b2b', name: '', birthDate: '', gradeOrGroup: '', gradeBand: 'PRIMARY_SECONDARY', isSecondChild: false }
        : {
            id: deal?.child.id ?? `c${Date.now()}`,
            parentId: deal?.parent.id ?? (duplicateMatch?.id || ''),
            name: childName,
            birthDate: deal?.child.birthDate ?? '',
            gradeOrGroup,
            gradeBand: deal?.child.gradeBand ?? 'PRIMARY_SECONDARY',
            isSecondChild,
          },
      branchId,
      tariffId: selectedTariff?.id ?? '',
      hasFood: isB2BMode ? false : hasFood,
      hasTransport: isB2BMode ? false : hasTransport,
      addons: { food: isB2BMode ? false : hasFood, transport: isB2BMode ? false : hasTransport },
      isWaitlisted: isB2BMode ? false : isWaitlisted,
      totalAmount: isB2BMode ? (b2bBudgetNum || deal?.contractValue || 0) : (serverPreview ? Number(serverPreview.total_amount) : (calcTotal())),
      expectedRevenue: isB2BMode ? (b2bBudgetNum || deal?.contractValue || 0) : (serverPreview ? Number(serverPreview.total_amount) : (calcTotal())),
      contractValue: isB2BMode ? (b2bBudgetNum || deal?.contractValue || 0) : undefined,
      partnerType: isB2BMode ? b2bServiceType : undefined,
      b2b: isB2BMode
        ? {
            companyName: b2bCompany,
            bin: b2bBin,
            contactPerson: b2bContactPerson,
            position: b2bPosition,
            phone: b2bPhone,
            email: b2bEmail,
            serviceType: b2bServiceType,
            budget: b2bBudgetNum || 0,
          }
        : undefined,
      // Гео-роутинг + анти-дубль
      sourceCity,
      sourceBranchRequested,
      isCrossBranch: isCrossBranchLead,
      contactId: attachToExisting ? duplicateMatch?.id : undefined,
      isDuplicateOf: attachToExisting ? duplicateMatch?.id : undefined,
      paymentSchedule,
    }

    if (isCreateMode) {
      onCreateDeal?.(payload as Partial<Deal>)
    } else {
      onSaveDeal?.(payload)
    }
    onClose()
  }

  function calcTotal(): number {
    if (serverPreview) return Number(serverPreview.total_amount)
    return 0
  }

  const canDelete = canDeleteDeal(currentUser ?? null)
  const canMarkPaid = canMarkPaymentPaid(currentUser ?? null)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div className="w-full max-w-5xl max-h-[92vh] overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-slate-400">{isCreateMode ? 'New deal' : 'Deal details'}</p>
            <h2 className="text-2xl font-bold text-slate-900">
              {isB2BMode ? (b2bCompany || 'Создать B2B-сделку') : (parentName || 'Create a new opportunity')}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {isB2BMode
                ? `${b2bServiceType || 'B2B-услуга'} • ${mockBranches.find((b) => b.id === branchId)?.name ?? 'No branch'}`
                : `${childName || 'No child linked yet'} • ${mockBranches.find((b) => b.id === branchId)?.name ?? 'No branch'}`}
            </p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>

        {/* Предупреждение о кросс-филиальном лиде (раздел 8.5) */}
        {isCrossBranchLead && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            ⚠️ Вы выбрали филиал <b>{mockBranches.find((b) => b.id === branchId)?.name}</b>, но лид интересуется
            филиалом <b>{requestedBranch?.name}</b>. Будет создана связанная кросс-филиальная сделка.
          </div>
        )}

        {/* Плашка анти-дубля (раздел 7, Риск 4) */}
        {duplicateMatch && (
          <DuplicateContactBanner
            match={duplicateMatch}
            attachToExisting={attachToExisting}
            onAttach={() => setAttachToExisting(true)}
          />
        )}

        {/* Вкладки */}
        <div className="mt-6 flex gap-2 rounded-full bg-slate-100 p-1 w-fit">
          {(
            [
              ['people', isB2BMode ? 'Заказчик и Проект' : 'Родитель и ребёнок', isB2BMode ? Briefcase : User],
              ['tariff', isB2BMode ? 'Бюджет и Услуга' : 'Тариф и доп. услуги', CreditCard],
              ['schedule', 'График платежей', CalendarDays],
            ] as Array<[ModalTab, string, typeof User]>
          ).map(([tabId, label, Icon]) => (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition ${
                activeTab === tabId ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {/* ───────── Вкладка 1: Заказчик и Проект (B2B) / Родитель и ребёнок (B2C) ───────── */}
          {activeTab === 'people' && (
            isB2BMode ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 p-4 space-y-3">
                  <h3 className="text-sm font-semibold text-slate-900">Компания / Организация</h3>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Название компании</label>
                    <input value={b2bCompany} onChange={(e) => setB2bCompany(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" placeholder="ТОО «BI Group»" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">БИН / ИИН</label>
                    <input value={b2bBin} maxLength={12} onChange={(e) => setB2bBin(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" placeholder="123456789012" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Телефон</label>
                    <input value={b2bPhone} onChange={(e) => setB2bPhone(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Email</label>
                    <input value={b2bEmail} onChange={(e) => setB2bEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4 space-y-3">
                  <h3 className="text-sm font-semibold text-slate-900">Контактное лицо</h3>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">ФИО</label>
                    <input value={b2bContactPerson} onChange={(e) => setB2bContactPerson(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" placeholder="Иванов Иван Иванович" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Должность</label>
                    <input value={b2bPosition} onChange={(e) => setB2bPosition(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" placeholder="Директор по развитию" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Тип услуги</label>
                    <select value={b2bServiceType} onChange={(e) => setB2bServiceType(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm">
                      <option>Франчайзинг</option>
                      <option>Строительство</option>
                      <option>Консалтинг</option>
                      <option>Управление</option>
                    </select>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 p-4 space-y-3">
                  <h3 className="text-sm font-semibold text-slate-900">Родитель</h3>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">ФИО</label>
                    <input value={parentName} onChange={(e) => setParentName(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Телефон</label>
                    <input value={parentPhone} onChange={(e) => setParentPhone(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                    {isCheckingDuplicate && <p className="mt-1 text-[11px] text-slate-400">Проверка дублей...</p>}
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">ИИН</label>
                    <input value={parentIin} maxLength={12} onChange={(e) => setParentIin(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4 space-y-3">
                  <h3 className="text-sm font-semibold text-slate-900">Ребёнок</h3>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">ФИО ребёнка</label>
                    <input value={childName} onChange={(e) => setChildName(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Класс / группа</label>
                    <input value={gradeOrGroup} onChange={(e) => setGradeOrGroup(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" />
                  </div>
                </div>
              </div>
            )
          )}

          {/* ───────── Вкладка 2: Бюджет и Услуга (B2B) / Тариф и доп. услуги (B2C) ───────── */}
          {activeTab === 'tariff' && (
            <div className="space-y-4">
              {isB2BMode ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Филиал</label>
                    <select
                      value={branchId}
                      disabled={fixedBranchId !== null && fixedBranchId !== undefined}
                      onChange={(e) => { setBranchId(e.target.value); setTariffId('') }}
                      className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-50"
                    >
                      {mockBranches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Тип услуги</label>
                    <select value={b2bServiceType} onChange={(e) => setB2bServiceType(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm">
                      <option>Франчайзинг</option>
                      <option>Строительство</option>
                      <option>Консалтинг</option>
                      <option>Управление</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Бюджет проекта / Сумма договора</label>
                    <input
                      type="number"
                      min={0}
                      value={b2bBudget}
                      onChange={(e) => setB2bBudget(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm"
                      placeholder="0"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Source city</label>
                    <input value={sourceCity} onChange={(e) => setSourceCity(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" placeholder="Астана / Алматы / ..." />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500">Branch requested by lead</label>
                    <select value={sourceBranchRequested} onChange={(e) => setSourceBranchRequested(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm">
                      {mockBranches.map((b) => <option key={b.id} value={b.code}>{b.name} ({b.code})</option>)}
                    </select>
                  </div>
                </div>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-xs font-medium text-slate-500">Филиал</label>
                      <select
                        value={branchId}
                        disabled={fixedBranchId !== null && fixedBranchId !== undefined}
                        onChange={(e) => { setBranchId(e.target.value); setTariffId('') }}
                        className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-50"
                      >
                        {mockBranches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-500">Source city</label>
                      <input value={sourceCity} onChange={(e) => setSourceCity(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm" placeholder="Астана / Алматы / ..." />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-500">Branch requested by lead</label>
                      <select value={sourceBranchRequested} onChange={(e) => setSourceBranchRequested(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm">
                        {mockBranches.map((b) => <option key={b.id} value={b.code}>{b.name} ({b.code})</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-500">Тариф</label>
                      <select
                        value={selectedTariff?.id ?? ''}
                        disabled={pricingLocked && !isCreateMode}
                        onChange={(e) => setTariffId(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-50"
                      >
                        {availableTariffs.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                      {pricingLocked && !isCreateMode && (
                        <p className="mt-1 text-[11px] text-slate-400">Только HQ_ADMIN может редактировать тарифы (раздел 8.2)</p>
                      )}
                    </div>
                  </div>

                  {/* Тумблеры доп. услуг */}
                  <div className="flex flex-wrap gap-4 pt-1">
                    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={hasFood} onChange={(e) => setHasFood(e.target.checked)} /> Питание</label>
                    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={hasTransport} onChange={(e) => setHasTransport(e.target.checked)} /> Развозка</label>
                    {hasTransport && (
                      <label className="flex items-center gap-2 text-sm">
                        <select value={transportZone} onChange={(e) => setTransportZone(e.target.value as 'CITY' | 'SUBURB')} className="rounded-lg border border-slate-200 p-1.5 text-sm">
                          <option value="CITY">Город</option>
                          <option value="SUBURB">Пригород</option>
                        </select>
                      </label>
                    )}
                    {isAldiBranch && (
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={isSecondChild} onChange={(e) => setIsSecondChild(e.target.checked)} />
                        Скидка 10% на 2-го ребёнка (ALDI BI)
                      </label>
                    )}
                    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={isWaitlisted} onChange={(e) => setIsWaitlisted(e.target.checked)} /> Лист ожидания</label>
                  </div>

                  {/* Результат калькулятора */}
                  {previewError ? (
                    <div className="rounded-2xl bg-rose-50 border border-rose-200 p-4 text-sm text-rose-700">
                      ⚠️ {previewError}
                    </div>
                  ) : serverPreview ? (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 space-y-2">
                      <div className="flex justify-between font-semibold text-slate-900 text-base">
                        <span>Итоговая стоимость</span>
                        <span>{Number(serverPreview.total_amount).toLocaleString('ru-RU')} ₸</span>
                      </div>
                      <div className="flex justify-between text-sm text-slate-500">
                        <span>Вступительный взнос</span>
                        <span>{Number(serverPreview.entrance_fee).toLocaleString('ru-RU')} ₸</span>
                      </div>
                      <div className="border-t border-slate-200 pt-2">
                        <p className="text-xs font-medium text-slate-500 mb-2">Предварительный график ({serverPreview.schedules.length} платежей):</p>
                        <div className="max-h-44 overflow-y-auto rounded-xl border border-slate-200 divide-y divide-slate-100">
                          {serverPreview.schedules.map((s, i) => (
                            <div key={i} className="flex items-center justify-between px-3 py-2 text-xs">
                              <span className="font-medium text-slate-700">{s.title}</span>
                              <span className="text-slate-500">
                                {new Date(s.due_date).toLocaleDateString('ru-RU')}
                              </span>
                              <span className="font-semibold text-slate-900">
                                {Number(s.amount).toLocaleString('ru-RU')} ₸
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">Выберите тариф — калькулятор загрузит предварительный расчёт...</p>
                  )}
                </>
              )}
            </div>
          )}

          {/* ───────── Вкладка 3: График платежей ───────── */}
          {activeTab === 'schedule' && (
            <div className="space-y-4">
              <PaymentScheduleList
                schedules={paymentSchedule ?? (serverPreview ? serverPreview.schedules.map((s, i) => ({
                  id: `preview-${i}`,
                  title: s.title,
                  due_date: s.due_date,
                  amount: s.amount,
                  status: s.status as PaymentScheduleEntry['status'],
                })) : undefined)}
                canMarkPaid={canMarkPaid}
                onMarkPaid={handleMarkPaid}
                tasks={deal?.tasks ?? []}
              />
              {canMarkPaid && (
                <p className="text-xs text-slate-400">
                  💡 Кнопка «Отметить оплаченным» доступна только HQ_ADMIN и BRANCH_DIRECTOR (раздел 8.2).
                </p>
              )}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3 border-t pt-4">
          {/* Кнопка «Удалить сделку» — только HQ_ADMIN/BRANCH_DIRECTOR (раздел 8.2) */}
          {!isCreateMode && canDelete && (
            <button onClick={() => onDeleteDeal?.(deal?.id ?? '')} className="mr-auto text-sm font-medium text-rose-600">Delete deal</button>
          )}
          <button onClick={onClose} className="rounded-xl border px-4 py-2 text-sm font-medium">Cancel</button>
          <button
            onClick={handleSave}
            disabled={isCreateMode && Boolean(duplicateMatch) && !attachToExisting}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isCreateMode ? 'Create deal' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DealModal
