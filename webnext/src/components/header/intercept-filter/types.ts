export type FilterCommand = {
  filter: string;
  description: string;
  category: string;
  requiresValue: boolean;
  valueType?: string;
};
