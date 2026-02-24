import React, { useState, useEffect } from 'react';
import { membersAPI } from '../api/members';
import Header from '../components/layout/Header';
import MemberCard from '../components/members/MemberCard';
import Select from '../components/common/Select';
import Button from '../components/common/Button';

const VetterDashboard = () => {
  const [members, setMembers] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [gettingNext, setGettingNext] = useState(false);
  const [message, setMessage] = useState('');
  const [pendingCount, setPendingCount] = useState(null);

  useEffect(() => {
    loadMembers();
    loadQueueCount();
  }, [statusFilter]);

  const loadQueueCount = async () => {
    try {
      const data = await membersAPI.getQueueCount();
      setPendingCount(data.pending_count);
    } catch (err) {
      console.error('Failed to load queue count:', err);
    }
  };

  const loadMembers = async () => {
    setLoading(true);
    try {
      const data = await membersAPI.list(statusFilter || null);
      setMembers(data);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGetNextCandidate = async () => {
    setGettingNext(true);
    setMessage('');
    try {
      const nextMember = await membersAPI.getNextCandidate();
      if (nextMember) {
        setMessage('New candidate assigned!');
        loadMembers();
        loadQueueCount();
      } else {
        setMessage('No pending candidates available.');
        setPendingCount(0);
      }
    } catch (err) {
      console.error('Failed to get next candidate:', err);
      setMessage('Error getting next candidate.');
    } finally {
      setGettingNext(false);
    }
  };

  const assignedMembers = members.filter((m) => m.status === 'ASSIGNED');
  const vettedMembers = members.filter((m) => m.status === 'VETTED');
  const rejectedMembers = members.filter((m) => m.status === 'REJECTED');
  const unsureMembers = members.filter((m) => m.status === 'UNSURE');

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">My Assigned Members</h1>
              {pendingCount !== null && (
                <p className="text-sm text-gray-600 mt-1">
                  {pendingCount === 0
                    ? 'No candidates waiting in the queue'
                    : `${pendingCount} candidate${pendingCount === 1 ? '' : 's'} waiting in the queue`}
                </p>
              )}
            </div>
            {pendingCount === 0 ? (
              <span className="inline-flex items-center px-4 py-2 bg-green-100 text-green-800 text-sm font-medium rounded-lg border border-green-300">
                Queue Empty - All Caught Up!
              </span>
            ) : (
              <Button
                onClick={handleGetNextCandidate}
                disabled={gettingNext}
              >
                {gettingNext ? 'Getting Next...' : 'Get Next Candidate'}
              </Button>
            )}
          </div>

          {message && (
            <div className={`mb-4 p-3 rounded ${
              message.includes('Error') ? 'bg-red-100 text-red-700' :
              message.includes('No pending') ? 'bg-yellow-100 text-yellow-700' :
              'bg-green-100 text-green-700'
            }`}>
              {message}
            </div>
          )}

          <div className="flex gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg shadow flex-1 border-l-4 border-yellow-400">
              <p className="text-sm text-gray-600">In Queue</p>
              <p className="text-2xl font-bold text-yellow-600">{pendingCount !== null ? pendingCount : '...'}</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow flex-1">
              <p className="text-sm text-gray-600">Assigned to Me</p>
              <p className="text-2xl font-bold text-blue-600">{assignedMembers.length}</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow flex-1">
              <p className="text-sm text-gray-600">Vetted</p>
              <p className="text-2xl font-bold text-green-600">{vettedMembers.length}</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow flex-1">
              <p className="text-sm text-gray-600">Unsure</p>
              <p className="text-2xl font-bold text-orange-600">{unsureMembers.length}</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow flex-1">
              <p className="text-sm text-gray-600">Rejected</p>
              <p className="text-2xl font-bold text-red-600">{rejectedMembers.length}</p>
            </div>
          </div>

          <div className="max-w-xs">
            <Select
              label="Filter by Status"
              name="status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: '', label: 'All' },
                { value: 'ASSIGNED', label: 'Assigned' },
                { value: 'VETTED', label: 'Vetted' },
                { value: 'UNSURE', label: 'Unsure' },
                { value: 'REJECTED', label: 'Rejected' },
              ]}
            />
          </div>
        </div>

        {loading ? (
          <p className="text-gray-600">Loading...</p>
        ) : members.length === 0 ? (
          <p className="text-gray-600">No members assigned to you yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {members.map((member) => (
              <MemberCard key={member.id} member={member} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VetterDashboard;
