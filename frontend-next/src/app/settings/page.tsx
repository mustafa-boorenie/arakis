'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/store';
import { api } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Loader2, Save, User, Mail, Phone, Building } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const user = useStore((state) => state.auth.user);
  const setUser = useStore((state) => state.setUser);
  const isAuthenticated = useStore((state) => state.auth.isAuthenticated);

  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [affiliation, setAffiliation] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated && !user) {
      router.push('/');
    }
  }, [isAuthenticated, user, router]);

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setPhoneNumber(user.phone_number || '');
      setAffiliation(user.affiliation || '');
    }
  }, [user]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);

    try {
      const updatedUser = await api.updateUser({
        full_name: fullName || undefined,
        phone_number: phoneNumber || undefined,
        affiliation: affiliation || undefined,
      });
      setUser(updatedUser);
      setSaveMessage({ type: 'success', text: 'Settings saved successfully!' });
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveMessage({ type: 'error', text: 'Failed to save settings. Please try again.' });
    } finally {
      setIsSaving(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button variant="ghost" size="icon" onClick={() => router.push('/')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-muted-foreground">Manage your account settings</p>
          </div>
        </div>

        {/* Profile Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Profile Information
            </CardTitle>
            <CardDescription>
              Update your personal information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Email (read-only) */}
            <div className="space-y-2">
              <Label htmlFor="email" className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={user.email}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">
                Email cannot be changed. Signed in via {user.auth_provider}.
              </p>
            </div>

            {/* User ID (read-only) */}
            <div className="space-y-2">
              <Label htmlFor="userId">User ID</Label>
              <Input
                id="userId"
                value={user.id}
                disabled
                className="bg-muted font-mono text-sm"
              />
            </div>

            {/* Full Name */}
            <div className="space-y-2">
              <Label htmlFor="fullName" className="flex items-center gap-2">
                <User className="w-4 h-4" />
                Full Name
              </Label>
              <Input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
              />
            </div>

            {/* Phone Number */}
            <div className="space-y-2">
              <Label htmlFor="phoneNumber" className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                Phone Number
              </Label>
              <Input
                id="phoneNumber"
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+1 (555) 123-4567"
              />
            </div>

            {/* Affiliation */}
            <div className="space-y-2">
              <Label htmlFor="affiliation" className="flex items-center gap-2">
                <Building className="w-4 h-4" />
                Affiliation
              </Label>
              <Input
                id="affiliation"
                type="text"
                value={affiliation}
                onChange={(e) => setAffiliation(e.target.value)}
                placeholder="University or Organization"
              />
            </div>

            {/* Save Button */}
            <div className="pt-4">
              <Button onClick={handleSave} disabled={isSaving} className="w-full gap-2">
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Changes
                  </>
                )}
              </Button>
              {saveMessage && (
                <p className={`text-sm mt-2 text-center ${saveMessage.type === 'success' ? 'text-green-600' : 'text-destructive'}`}>
                  {saveMessage.text}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Account Stats Card */}
        <Card>
          <CardHeader>
            <CardTitle>Account Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">{user.total_workflows}</p>
                <p className="text-sm text-muted-foreground">Total Workflows</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">${user.total_cost.toFixed(2)}</p>
                <p className="text-sm text-muted-foreground">Total Cost</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Member since {new Date(user.created_at).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
