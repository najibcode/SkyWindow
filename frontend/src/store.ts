import { create } from 'zustand';

export interface Target {
  id: string;
  name: string;
  lat: number;
  lon: number;
  weight: number;
}

interface TargetStore {
  targets: Target[];
  addTarget: (target: Omit<Target, 'id'>) => void;
  removeTarget: (id: string) => void;
}

export const useTargetStore = create<TargetStore>((set) => ({
  targets: [],
  addTarget: (target) => set((state) => ({
    targets: [...state.targets, { ...target, id: `t_${Date.now()}` }]
  })),
  removeTarget: (id) => set((state) => ({
    targets: state.targets.filter((t) => t.id !== id)
  }))
}));
