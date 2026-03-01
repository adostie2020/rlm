import NextAuth from "next-auth";
import Atlassian from "next-auth/providers/atlassian";
import { authConfig } from "./auth.config";
import { UserType } from "../types/next-auth";

export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  ...authConfig,
  debug: true,
  secret: process.env.AUTH_SECRET || "fallback_secret_for_local_development_only",
  providers: [
    Atlassian({
      clientId: process.env.JIRA_CLIENT_ID as string,
      clientSecret: process.env.JIRA_CLIENT_SECRET as string,
      authorization: {
        params: {
          scope: "read:jira-user read:jira-work write:jira-work offline_access",
          prompt: "consent",
          audience: "api.atlassian.com",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account, trigger, session }) {
      if (user) {
        token.id = user.id as string;
        token.type = (user as any).type as UserType;
      }

      // If logging in via Atlassian, capture tokens
      if (account && account.provider === "atlassian") {
        token.jiraAccessToken = account.access_token;
        token.jiraRefreshToken = account.refresh_token as string;
        // The Atlassian providerAccountId is often the Cloud ID. We will store it.
        token.jiraCloudId = account.providerAccountId;
      }

      if (trigger === "update" && session) {
        // Allow updates to the session token
        if (session.jiraAccessToken) token.jiraAccessToken = session.jiraAccessToken;
        if (session.jiraRefreshToken) token.jiraRefreshToken = session.jiraRefreshToken;
        if (session.jiraCloudId) token.jiraCloudId = session.jiraCloudId;
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.type = token.type as UserType;
        session.user.jiraAccessToken = token.jiraAccessToken as string | undefined;
        session.user.jiraRefreshToken = token.jiraRefreshToken as string | undefined;
        session.user.jiraCloudId = token.jiraCloudId as string | undefined;
      }

      return session;
    },
  },
});
