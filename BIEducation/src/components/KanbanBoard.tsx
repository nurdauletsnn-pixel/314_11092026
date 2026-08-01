import React from 'react';
import { filterDealsByAccess } from '../services/accessControl';
// Импортируйте функцию валидации (или объявите её выше)
  import { getPipelineStages, isValidStageTransition } from '../services/pipelineManager';

import type { Deal } from '../../bi-crm-demo/frontend/src/types';

interface KanbanBoardProps {
  deals: Deal[];
}

import type { CurrentUser } from '../../bi-crm-demo/frontend/src/types';

const KanbanBoard = ({ deals: initialDeals }: KanbanBoardProps) => {
  const selectedPipeline: "school" | "kindergarten" | "b2b" = 'school';
const currentUser: CurrentUser = { id: 'current-user', name: 'Current User', role: 'admin', allowedBranchIds: [] };

  const pipelineStages = getPipelineStages(selectedPipeline);
  // Передаем реальный массив сделок, а не строку 'deals-array'
  const deals = filterDealsByAccess(initialDeals, currentUser);

  return (
    <div className="flex gap-4">
      {pipelineStages.map((stage) => (
        <div key={stage.id} className="w-64 bg-gray-100 p-4 rounded">
          <h3 className="font-bold mb-2">{stage.name}</h3>
          
          {deals
            .filter((deal) => deal.stageId === stage.id)
            .map((deal) => (
              <div 
                key={deal.id} 
                className="p-3 bg-white mb-2 rounded shadow cursor-pointer"
                onMouseDown={() => {
                    if (isValidStageTransition(selectedPipeline, deal.stageId, stage.id)) {

                    // Логика перемещения карточки
                  } else {
                    // Обработка невалидного перехода
                  }
                }}
              >
                {deal.id}
              </div>
            ))}
        </div>
      ))}
    </div>
  );
};

export default KanbanBoard;

