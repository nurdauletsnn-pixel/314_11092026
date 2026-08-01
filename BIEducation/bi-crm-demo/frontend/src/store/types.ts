export interface CurrentUser {
  id?: string
  name?: string
  role: 'sales' | 'admin' | 'manager' | string
}

export interface Parent {
  id?: string
  name?: string
  phone?: string
  email?: string
  iin?: string
}

export interface Child {
  id?: string
  name?: string
  gradeOrGroup?: string
  gradeBand?: string
  birthDate?: string
}

export interface DealTask {
  id: string
  title: string
  dueDate: string
  isDone: boolean
}

export interface DealHistoryEntry {
  id: string
  type: string
  description: string
  timestamp: string
}

export interface Deal {
  id: string
  parent: Parent
  child: Child
  branchId: string
  pipelineId: 'school' | 'kindergarten' | 'b2b' | string
  stageId: string
  tariffId: string
  addons: {
    food: boolean
    transport: boolean
  }
  isWaitlisted: boolean
  expectedRevenue: number
  tasks: DealTask[]
  history: ActivityLog[]
}

export interface ActivityLog {
  id: string
  type: string
  content: string
  timestamp: string
}