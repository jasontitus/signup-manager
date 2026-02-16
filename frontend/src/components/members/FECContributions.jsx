import React, { useState, useEffect } from 'react';

const isDebugApi = () =>
  import.meta.env.VITE_DEBUG_API === 'true' ||
  localStorage.getItem('debug_api') === 'true';

const FECContributions = ({ firstName, lastName, zipCode }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!firstName || !lastName) return;

    const params = new URLSearchParams({
      first_name: firstName,
      last_name: lastName,
    });
    if (zipCode) params.set('zip_code', zipCode);

    setLoading(true);
    setError('');

    const debug = isDebugApi();
    const url = `/contributions/api/person?${params}`;
    const startTime = performance.now();

    if (debug) {
      const paramKeys = Array.from(params.keys()).join(', ');
      console.debug(`[FEC API] GET /contributions/api/person params=[${paramKeys}]`);
    }

    fetch(url)
      .then((res) => {
        if (debug) {
          const elapsed = (performance.now() - startTime).toFixed(0);
          console.debug(`[FEC API] Response: ${res.status} in ${elapsed}ms`);
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (debug) {
          const fecCount = json?.fec?.contributions?.length ?? 0;
          const caCount = json?.ca?.contributions?.length ?? 0;
          console.debug(`[FEC API] Payload: ${fecCount} FEC + ${caCount} CA contributions`);
          if (json?._timings) {
            console.debug('[FEC API] Server timings:', JSON.stringify(json._timings, null, 2));
          }
        }
        setData(json);
      })
      .catch((err) => {
        if (debug) {
          const elapsed = (performance.now() - startTime).toFixed(0);
          console.debug(`[FEC API] Error after ${elapsed}ms: ${err.message}`);
        }
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [firstName, lastName, zipCode]);

  if (loading) {
    return (
      <div className="mb-6 border-t pt-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Campaign Contributions</h2>
        <p className="text-gray-500">Loading contributions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mb-6 border-t pt-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Campaign Contributions</h2>
        <p className="text-red-600">Failed to load contributions: {error}</p>
      </div>
    );
  }

  const fecContribs = data?.fec?.contributions || [];
  const caContribs = data?.ca?.contributions || [];
  const fecTotal = data?.fec?.total_giving || 0;
  const caTotal = data?.ca?.total_giving || 0;
  const percentiles = data?.percentiles || {};
  const hasAny = fecContribs.length > 0 || caContribs.length > 0;

  const formatCurrency = (amount) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const ContributionTable = ({ contributions, label, total }) => {
    if (contributions.length === 0) return null;
    return (
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-sm font-semibold text-gray-700">{label}</h3>
          <span className="text-sm font-medium text-gray-600">
            Total: {formatCurrency(total)}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-4 text-gray-600 font-medium">Date</th>
                <th className="text-left py-2 pr-4 text-gray-600 font-medium">Recipient</th>
                <th className="text-right py-2 text-gray-600 font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {contributions.map((c, i) => (
                <tr key={i} className="border-b border-gray-100">
                  <td className="py-2 pr-4 text-gray-700 whitespace-nowrap">{c.contribution_date}</td>
                  <td className="py-2 pr-4 text-gray-700">{c.recipient_name}</td>
                  <td className="py-2 text-right text-gray-700">{formatCurrency(c.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const percentileYears = Object.keys(percentiles).sort().reverse();

  return (
    <div className="mb-6 border-t pt-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Campaign Contributions</h2>

      {data?.cascade_message && (
        <p className="text-sm text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-3 py-2 mb-4">
          Search was broadened: {data.cascade_message}
        </p>
      )}

      {!hasAny ? (
        <p className="text-gray-500 italic">No contributions found</p>
      ) : (
        <>
          <ContributionTable
            contributions={fecContribs}
            label="Federal (FEC)"
            total={fecTotal}
          />
          <ContributionTable
            contributions={caContribs}
            label="California (CalAccess)"
            total={caTotal}
          />

          {percentileYears.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Donor Percentile Ranking</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {percentileYears.map((year) => {
                  const p = percentiles[year];
                  return (
                    <div key={year} className="bg-gray-50 rounded p-3 text-center">
                      <p className="text-xs text-gray-500">{year}</p>
                      <p className="text-lg font-bold text-gray-900">
                        {p.percentile.toFixed(1)}%
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatCurrency(p.total_amount)} ({p.contribution_count} gifts)
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default FECContributions;
