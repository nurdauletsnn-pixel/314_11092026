// import type { ActivityLog, Branch, Child, CurrentUser, Deal, Parent, Tariff, Task } from '../types'

// export const mockBranches: Branch[] = [
//   { id: '1', code: 'RIVIERA', name: 'Riviera International School', city: 'Астана', segment: 'School' },
//   { id: '2', code: 'QUANTUM_STEM', name: 'Quantum STEM School', city: 'Астана', segment: 'STEM' },
//   { id: '3', code: 'ALDI_BI', name: 'ALDI BI Capital Park', city: 'Алматы', segment: 'Kindergarten' },
//   { id: '4', code: 'BIART', name: 'BIART', city: 'Астана', segment: 'B2B' },
// ]

// export const mockParents: Parent[] = [
//   { id: 'p1', name: 'Айгерим Толегенова', phone: '+7 701 111 22 33' },
//   { id: 'p2', name: 'Нурлан Бектемиров', phone: '+7 707 222 44 55' },
//   { id: 'p3', name: 'Мадияр Сарсенов', phone: '+7 700 333 66 77' },
//   { id: 'p4', name: 'Дана Хамзина', phone: '+7 705 444 88 99' },
// ]

// export const mockChildren: Child[] = [
//   { id: 'c1', parentId: 'p1', name: 'Аружан Толегенова', birthDate: '2020-01-15', gradeOrGroup: '1 класс', gradeBand: 'PRIMARY_SECONDARY' },
//   { id: 'c2', parentId: 'p2', name: 'Ерасыл Бектемиров', birthDate: '2018-09-21', gradeOrGroup: 'Младшая группа', gradeBand: 'PRESCHOOL' },
//   { id: 'c3', parentId: 'p3', name: 'Самал Сарсенова', birthDate: '2022-03-05', gradeOrGroup: 'Старшая группа', gradeBand: 'PRESCHOOL' },
//   { id: 'c4', parentId: 'p4', name: 'Арман Хамзин', birthDate: '2019-07-11', gradeOrGroup: '2 класс', gradeBand: 'PRIMARY_SECONDARY' },
// ]

// export const mockTariffs: Tariff[] = [
//   { id: 't1', branchCode: 'RIVIERA', name: 'Выгодный', grade_band: 'PRIMARY_SECONDARY', base_amount: 4500000, entrance_fee: 350000 },
//   { id: 't2', branchCode: 'RIVIERA', name: 'Стандарт', grade_band: 'PRIMARY_SECONDARY', base_amount: 4900000, entrance_fee: 350000 },
//   { id: 't3', branchCode: 'QUANTUM_STEM', name: 'Основной (9 траншей)', grade_band: 'PRIMARY_SECONDARY', base_amount: 4410000, entrance_fee: 200000 },
//   { id: 't4', branchCode: 'ALDI_BI', name: 'Помесячно 250k', grade_band: 'PRESCHOOL', base_amount: 2500000, entrance_fee: 200000 },
//   { id: 't5', branchCode: 'BIART', name: 'Корпоративный', grade_band: 'PRIMARY_SECONDARY', base_amount: 5000000, entrance_fee: 0 },
// ]

// const mockTasks = (title: string, dueDate: string): Task => ({ id: `${title}-${dueDate}`, title, isDone: false, dueDate })
// const mockActivities = (description: string, timestamp: string): Activity => ({ id: `${description}-${timestamp}`, type: 'System', description, timestamp })
// export const mockDeals: Deal[] = [
//   {
//     id: 'd1',
//     parent: mockParents[0],
//     child: mockChildren[0],
//     branchId: '1', // id из mockBranches (RIVIERA)
//     pipelineId: 'school',
//     stageId: 'qualification',
//     status: 'ACTIVE',
//     tariffId: 't2', // id из mockTariffs (Стандарт)
//     hasFood: true,
//     hasTransport: true,
//     totalAmount: 5252400,
//     expectedRevenue: 5252400,
//     tasks: [mockTasks('Перезвонить завтра', '2026-08-01'), mockTasks('Отправить ссылку на оплату', '2026-08-02')],
//     history: [mockActivities('WhatsApp бот отправил приветствие', '2026-07-28T09:00:00Z'), mockActivities('Этап изменен на Квалификация', '2026-07-29T10:30:00Z')],
//     addons: { food: true, transport: true },
//     isWaitlisted: false,
//   },
//   {
//     id: 'd2',
//     parent: mockParents[1],
//     child: mockChildren[1],
//     branchId: '3', // id из mockBranches (ALDI_BI)
//     pipelineId: 'kindergarten',
//     stageId: 'tour',
//     status: 'ACTIVE',
//     tariffId: 't4', // id из mockTariffs (Помесячно 250k)
//     hasFood: true,
//     hasTransport: false,
//     totalAmount: 2700000,
//     expectedRevenue: 2700000,
//     tasks: [mockTasks('Подтвердить пробный день', '2026-07-31')],
//     history: [mockActivities('Запись на экскурсию', '2026-07-27T16:45:00Z')],
//     addons: { food: true, transport: false },
//     isWaitlisted: true,
//   },
// ]

// // export const mockDeals: Deal[] = [
// //   {
// //     id: 'd1',
// //     parentId: 'p1',
// //     childId: 'c1',
// //     branch_code: 'RIVIERA',
// //     pipelineId: 'school',
// //     stageId: 'qualification',
// //     tariff_name: 'Стандарт',
// //     addons: { food: true, transport: true },
// //     isWaitlisted: false,
// //     expectedRevenue: 5252400,
// //     parent: mockParents[0],
// //     child: mockChildren[0],
// //     branch: mockBranches[0],
// //     tariff: mockTariffs[1],
// //     tasks: [mockTasks('Перезвонить завтра', '2026-08-01'), mockTasks('Отправить ссылку на оплату', '2026-08-02')],
// //     history: [mockActivities('WhatsApp бот отправил приветствие', '2026-07-28T09:00:00Z'), mockActivities('Этап изменен на Квалификация', '2026-07-29T10:30:00Z')],
// //   },
// //   {
// //     id: 'd2',
// //     parentId: 'p2',
// //     childId: 'c2',
// //     branch_code: 'ALDI_BI',
// //     pipelineId: 'kindergarten',
// //     stageId: 'tour',
// //     tariff_name: 'Помесячно 250k',
// //     addons: { food: true, transport: false },
// //     isWaitlisted: true,
// //     expectedRevenue: 2700000,
// //     parent: mockParents[1],
// //     child: mockChildren[1],
// //     branch: mockBranches[2],
// //     tariff: mockTariffs[3],
// //     tasks: [mockTasks('Подтвердить пробный день', '2026-07-31')],
// //     history: [mockActivities('Запись на экскурсию', '2026-07-27T16:45:00Z')],
// //   },
// // ]

// export const mockUsers: Record<'salesManager' | 'hqAdmin', CurrentUser> = {
//   salesManager: {
//     id: 'u1',
//     name: 'Менеджер продаж',
//     role: 'sales',
//     allowedBranchIds: ['1', '3'],
//   },
//   hqAdmin: {
//     id: 'u2',
//     name: 'Администратор ГО',
//     role: 'hq_admin',
//     allowedBranchIds: ['1', '2', '3', '4'],
//   },
// }

import type { ActivityLog, Branch, Child, CurrentUser, Deal, Parent, Tariff, Task } from '../types'

export const mockBranches: Branch[] = [
  { id: '1', code: 'RIVIERA', name: 'Riviera International School', city: 'Астана', segment: 'School' },
  { id: '2', code: 'QUANTUM_STEM', name: 'Quantum STEM School', city: 'Астана', segment: 'STEM' },
  { id: '3', code: 'ALDI_BI', name: 'ALDI BI Capital Park', city: 'Алматы', segment: 'Kindergarten' },
  { id: '4', code: 'BIART', name: 'BIART', city: 'Астана', segment: 'B2B' },
]

export const mockParents: Parent[] = [
  { id: 'p1', name: 'Айгерим Толегенова', phone: '+7 701 111 22 33' },
  { id: 'p2', name: 'Нурлан Бектемиров', phone: '+7 707 222 44 55' },
  { id: 'p3', name: 'Мадияр Сарсенов', phone: '+7 700 333 66 77' },
  { id: 'p4', name: 'Дана Хамзина', phone: '+7 705 444 88 99' },
]

export const mockChildren: Child[] = [
  { id: 'c1', parentId: 'p1', name: 'Аружан Толегенова', birthDate: '2020-01-15', gradeOrGroup: '1 класс', gradeBand: 'PRIMARY_SECONDARY' },
  { id: 'c2', parentId: 'p2', name: 'Ерасыл Бектемиров', birthDate: '2018-09-21', gradeOrGroup: 'Младшая группа', gradeBand: 'PRESCHOOL' },
  { id: 'c3', parentId: 'p3', name: 'Самал Сарсенова', birthDate: '2022-03-05', gradeOrGroup: 'Старшая группа', gradeBand: 'PRESCHOOL' },
  { id: 'c4', parentId: 'p4', name: 'Арман Хамзин', birthDate: '2019-07-11', gradeOrGroup: '2 класс', gradeBand: 'PRIMARY_SECONDARY' },
]

export const mockTariffs: Tariff[] = [
  { id: 't1', branchCode: 'RIVIERA', name: 'Выгодный', grade_band: 'PRIMARY_SECONDARY', base_amount: 4500000, entrance_fee: 350000 },
  { id: 't2', branchCode: 'RIVIERA', name: 'Стандарт', grade_band: 'PRIMARY_SECONDARY', base_amount: 4900000, entrance_fee: 350000 },
  { id: 't3', branchCode: 'QUANTUM_STEM', name: 'Основной (9 траншей)', grade_band: 'PRIMARY_SECONDARY', base_amount: 4410000, entrance_fee: 200000 },
  { id: 't4', branchCode: 'ALDI_BI', name: 'Помесячно 250k', grade_band: 'PRESCHOOL', base_amount: 2500000, entrance_fee: 200000 },
  { id: 't5', branchCode: 'BIART', name: 'Корпоративный', grade_band: 'PRIMARY_SECONDARY', base_amount: 5000000, entrance_fee: 0 },
]

const mockTasks = (title: string, dueDate: string): Task => ({
  id: `${title}-${dueDate}`,
  title,
  isDone: false,
  dueDate,
})

const mockActivities = (description: string, timestamp: string): ActivityLog => ({
  id: `${description}-${timestamp}`,
  type: 'SYSTEM',
  description,
  timestamp,
})

export const mockDeals: Deal[] = [
  {
    id: 'd1',
    parent: mockParents[0],
    child: mockChildren[0],
    branchId: '1', // RIVIERA
    pipelineId: 'school',
    stageId: 'qualification',
    status: 'ACTIVE',
    tariffId: 't2', // Стандарт
    hasFood: true,
    hasTransport: true,
    totalAmount: 5252400,
    expectedRevenue: 5252400,
    tasks: [
      mockTasks('Перезвонить завтра', '2026-08-01'),
      mockTasks('Отправить ссылку на оплату', '2026-08-02'),
    ],
    history: [
      mockActivities('WhatsApp бот отправил приветствие', '2026-07-28T09:00:00Z'),
      mockActivities('Этап изменен на Квалификация', '2026-07-29T10:30:00Z'),
    ],
    addons: { food: true, transport: true },
    isWaitlisted: false,
  },
  {
    id: 'd2',
    parent: mockParents[1],
    child: mockChildren[1],
    branchId: '3', // ALDI_BI
    pipelineId: 'kindergarten',
    stageId: 'tour',
    status: 'ACTIVE',
    tariffId: 't4', // Помесячно 250k
    hasFood: true,
    hasTransport: false,
    totalAmount: 2700000,
    expectedRevenue: 2700000,
    tasks: [mockTasks('Подтвердить пробный день', '2026-07-31')],
    history: [mockActivities('Запись на экскурсию', '2026-07-27T16:45:00Z')],
    addons: { food: true, transport: false },
    isWaitlisted: true,
  },
  {
    id: 'd3',
    parent: mockParents[2],
    child: mockChildren[2],
    branchId: '2', // QUANTUM_STEM
    pipelineId: 'school',
    stageId: 'new',
    status: 'ACTIVE',
    tariffId: 't3', // Основной (9 траншей)
    hasFood: true,
    hasTransport: false,
    totalAmount: 4610000,
    expectedRevenue: 4610000,
    tasks: [mockTasks('Позвонить и уточнить дату визита', '2026-08-03')],
    history: [mockActivities('Заявка создана через сайт', '2026-07-30T14:20:00Z')],
    addons: { food: true, transport: false },
    isWaitlisted: false,
  },
  {
    id: 'd4',
    parent: mockParents[3],
    child: mockChildren[3],
    branchId: '1', // RIVIERA
    pipelineId: 'school',
    stageId: 'enrolled',
    status: 'WON',
    tariffId: 't1', // Выгодный
    hasFood: false,
    hasTransport: true,
    totalAmount: 4850000,
    expectedRevenue: 4850000,
    tasks: [],
    history: [
      mockActivities('Договор подписан', '2026-07-15T11:00:00Z'),
      mockActivities('Вступительный взнос оплачен', '2026-07-20T09:30:00Z'),
      mockActivities('Ученик зачислен', '2026-07-25T10:00:00Z'),
    ],
    addons: { food: false, transport: true },
    isWaitlisted: false,
  },
]

export const mockUsers: Record<'salesManager' | 'hqAdmin' | 'branchDirector', CurrentUser> = {
  salesManager: {
    id: 'u1',
    username: 'sales_manager',
    first_name: 'Менеджер',
    last_name: 'Продаж',
    role: 'SALES_MANAGER',
    branch: mockBranches[0],
  },
  branchDirector: {
    id: 'u2',
    username: 'branch_director',
    first_name: 'Директор',
    last_name: 'Филиала',
    role: 'BRANCH_DIRECTOR',
    branch: mockBranches[0],
  },
  hqAdmin: {
    id: 'u3',
    username: 'hq_admin',
    first_name: 'Администратор',
    last_name: 'ГО',
    role: 'HQ_ADMIN',
    branch: null,
  },
}
