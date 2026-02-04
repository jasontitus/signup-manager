import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { membersAPI } from '../api/members';
import Input from '../components/common/Input';
import Textarea from '../components/common/Textarea';
import Button from '../components/common/Button';

const PublicApplicationForm = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    street_address: '',
    city: '',
    zip_code: '',
    phone_number: '',
    email: '',
    occupational_background: '',
    know_member: '',
    hoped_impact: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const submitData = {
        ...formData,
        occupational_background: formData.occupational_background || null,
        know_member: formData.know_member || null,
        hoped_impact: formData.hoped_impact || null,
      };

      await membersAPI.submitApplication(submitData);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Application submission failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
        <div className="max-w-md w-full bg-white p-8 rounded-lg shadow">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
              <svg
                className="h-6 w-6 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Application Submitted!</h2>
            <p className="text-gray-600 mb-6">
              Thank you for your application. We will review it and contact you soon.
            </p>
            <Button onClick={() => navigate('/')}>Return to Home</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Membership Application
          </h2>

          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="First Name"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                required
              />
              <Input
                label="Last Name"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                required
              />
            </div>

            <Input
              label="Street Address"
              name="street_address"
              value={formData.street_address}
              onChange={handleChange}
              required
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="City"
                name="city"
                value={formData.city}
                onChange={handleChange}
                required
              />
              <Input
                label="Zip Code"
                name="zip_code"
                value={formData.zip_code}
                onChange={handleChange}
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Phone Number"
                name="phone_number"
                type="tel"
                value={formData.phone_number}
                onChange={handleChange}
                required
              />
              <Input
                label="Email Address (for newsletter)"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>

            <Textarea
              label="What is your occupational background? Feel free to share your LinkedIn if you like."
              name="occupational_background"
              value={formData.occupational_background}
              onChange={handleChange}
              placeholder="This helps us connect people to each other and to understand the skills and experience in the group."
            />

            <Textarea
              label="Do you know someone who is a current member? If so, who?"
              name="know_member"
              value={formData.know_member}
              onChange={handleChange}
            />

            <Textarea
              label="What impact do you hope to have by joining? (If you don't know, that's OK)"
              name="hoped_impact"
              value={formData.hoped_impact}
              onChange={handleChange}
            />

            {error && (
              <div className="rounded-md bg-red-50 p-4 mb-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            <div className="mt-6">
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? 'Submitting...' : 'Submit Application'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default PublicApplicationForm;
