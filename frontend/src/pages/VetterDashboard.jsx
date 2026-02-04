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

  useEffect(() => {
    loadMembers();
  }, [statusFilter]);

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
        loadMembers(); // Reload the list to show the new assignment
      } else {
        setMessage('No pending candidates available.');
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

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-3xl font-bold text-gray-900">My Assigned Members</h1>
            <Button
              onClick={handleGetNextCandidate}
              disabled={gettingNext}
            >
              {gettingNext ? 'Getting Next...' : 'Get Next Candidate'}
            </Button>
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
            <div className="bg-white p-4 rounded-lg shadow flex-1">
              <p className="text-sm text-gray-600">Assigned to Me</p>
              <p className="text-2xl font-bold text-blue-600">{assignedMembers.length}</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow flex-1">
              <p className="text-sm text-gray-600">Vetted</p>
              <p className="text-2xl font-bold text-green-600">{vettedMembers.length}</p>
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
