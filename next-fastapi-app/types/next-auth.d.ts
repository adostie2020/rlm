import { type DefaultSession } from "next-auth";
import { type DefaultJWT } from "next-auth/jwt";

export type UserType = "user" | "guest" | "regular";

declare module "next-auth" {
    interface Session {
        user: {
            id: string;
            type: UserType;
            jiraAccessToken?: string;
            jiraRefreshToken?: string;
            jiraCloudId?: string;
        } & DefaultSession["user"];
    }

    interface User {
        id?: string;
        email?: string | null;
        type: UserType;
        jiraAccessToken?: string;
        jiraRefreshToken?: string;
        jiraCloudId?: string;
    }
}

declare module "next-auth/jwt" {
    interface JWT extends DefaultJWT {
        id: string;
        type: UserType;
        jiraAccessToken?: string;
        jiraRefreshToken?: string;
        jiraCloudId?: string;
    }
}
