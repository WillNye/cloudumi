export interface DataTable<T> {
  filtered_count: number;
  pages: number;
  page_size: number;
  current_page_index: number;
  data: T[];
}
