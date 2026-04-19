import axios from 'axios';

// Consent types matching backend ConsentType
export type ConsentType =
    | 'privacy_policy'
    | 'terms_of_service'
    | 'ai_processing'
    | 'third_party_sharing'
    | 'research_use'
    | 'behavioral_tracking';

// Only self-service methods are accepted by the grant endpoint; the server
// rejects institutional/parental to keep the audit trail honest.
export type ConsentMethod = 'registration' | 'in_app';

export interface ConsentStatus {
    granted: boolean;
    granted_at: string | null;
    withdrawn_at: string | null;
    policy_version: string | null;
}

export interface ConsentRecord {
    consent_type: ConsentType;
    granted: boolean;
    granted_at: string;
    policy_version: string;
}

export interface DeletionStatus {
    status: string;
    deletion_requested_at?: string;
    deletion_scheduled_at?: string;
    grace_period_days?: number;
}

export interface AgeVerificationData {
    is_minor: boolean;
    is_child: boolean;
    date_of_birth?: string;
}

export interface NomineeData {
    nominee_name: string;
    nominee_email: string;
    nominee_relationship: string;
}

export interface UserDataExport {
    export_version: string;
    user_id: number;
    profile: Record<string, unknown>;
    submissions: Record<string, unknown>[];
    progress: Record<string, unknown>[];
    enrollments: Record<string, unknown>[];
    hint_activations: Record<string, unknown>[];
    ai_analyses: Record<string, unknown>[];
    consent_history: Record<string, unknown>[];
}

class PrivacyService {
    // Consent management
    async getConsents(): Promise<Record<ConsentType, ConsentStatus>> {
        const response = await axios.get('/api/users/me/consents/');
        return response.data;
    }

    async grantConsent(
        consentType: ConsentType,
        options?: { consent_method?: ConsentMethod },
    ): Promise<ConsentRecord> {
        const payload: { consent_type: ConsentType; consent_method?: ConsentMethod } = {
            consent_type: consentType,
        };
        if (options?.consent_method) {
            payload.consent_method = options.consent_method;
        }
        const response = await axios.post('/api/users/me/consents/', payload);
        return response.data;
    }

    async withdrawConsent(consentType: ConsentType): Promise<{ consent_type: string; granted: boolean; withdrawn_at: string }> {
        const response = await axios.delete(`/api/users/me/consents/${consentType}/`);
        return response.data;
    }

    // Data export
    async exportData(): Promise<UserDataExport> {
        const response = await axios.get('/api/users/me/data-export/');
        return response.data;
    }

    // Account deletion
    async requestDeletion(): Promise<DeletionStatus> {
        const response = await axios.delete('/api/users/me/delete/');
        return response.data;
    }

    async cancelDeletion(): Promise<DeletionStatus> {
        const response = await axios.post('/api/users/me/cancel-deletion/');
        return response.data;
    }

    // Age verification
    async getAgeVerification(): Promise<AgeVerificationData & { verified: boolean }> {
        const response = await axios.get('/api/users/me/age-verification/');
        return response.data;
    }

    async submitAgeVerification(data: AgeVerificationData): Promise<AgeVerificationData> {
        const response = await axios.post('/api/users/me/age-verification/', data);
        return response.data;
    }

    // Nominee (DPDPA)
    async getNominee(): Promise<NomineeData | { nominee: null }> {
        const response = await axios.get('/api/users/me/nominee/');
        return response.data;
    }

    async setNominee(data: NomineeData): Promise<NomineeData> {
        const response = await axios.post('/api/users/me/nominee/', data);
        return response.data;
    }

    async removeNominee(): Promise<void> {
        await axios.delete('/api/users/me/nominee/');
    }

    // Directory info (FERPA)
    async updateDirectoryInfoVisibility(visible: boolean): Promise<{ directory_info_visible: boolean }> {
        const response = await axios.patch('/api/users/me/directory-info/', {
            directory_info_visible: visible,
        });
        return response.data;
    }

    // Utility: trigger JSON download
    downloadAsJson(data: unknown, filename: string): void {
        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

export default new PrivacyService();
