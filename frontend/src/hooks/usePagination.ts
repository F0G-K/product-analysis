import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

export function usePagination(defaultPageSize = 20) {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = useMemo(() => {
    const p = searchParams.get('page');
    return p ? Math.max(1, parseInt(p, 10)) : 1;
  }, [searchParams]);

  const pageSize = useMemo(() => {
    const ps = searchParams.get('page_size');
    return ps ? Math.max(1, Math.min(100, parseInt(ps, 10))) : defaultPageSize;
  }, [searchParams, defaultPageSize]);

  const setPage = useCallback(
    (p: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (p <= 1) {
          next.delete('page');
        } else {
          next.set('page', String(p));
        }
        return next;
      });
    },
    [setSearchParams],
  );

  const setPageSize = useCallback(
    (ps: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (ps === defaultPageSize) {
          next.delete('page_size');
        } else {
          next.set('page_size', String(ps));
        }
        next.delete('page'); // reset to page 1
        return next;
      });
    },
    [setSearchParams, defaultPageSize],
  );

  const offset = useMemo(() => (page - 1) * pageSize, [page, pageSize]);

  return { page, pageSize, setPage, setPageSize, offset };
}
