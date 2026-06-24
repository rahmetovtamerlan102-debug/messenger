package com.example.messenger.network

import android.content.Context
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException

class AuthInterceptor(private val context: Context) : Interceptor {
    private val tokenManager = TokenManager(context)

    @Throws(IOException::class)
    override fun intercept(chain: Interceptor.Chain): Response {
        var request = chain.request()
        val token = tokenManager.getAccessToken()
        if (token != null) {
            request = request.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        }
        val response = chain.proceed(request)

        if (response.code == 401) {
            response.close()
            val refreshToken = tokenManager.getRefreshToken()
            if (refreshToken != null) {
                val newTokens = refreshAccessToken(refreshToken)
                if (newTokens != null) {
                    tokenManager.saveTokens(newTokens.first, newTokens.second)
                    val newRequest = request.newBuilder()
                        .header("Authorization", "Bearer ${newTokens.first}")
                        .build()
                    return chain.proceed(newRequest)
                }
            }
        }
        return response
    }

    private fun refreshAccessToken(refresh: String): Pair<String, String>? {
        try {
            val api = ApiClient.getApiService(context)
            val response = api.refreshToken(mapOf("refresh" to refresh)).execute()
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    val newAccess = body.access
                    val newRefresh = body.refresh ?: refresh
                    return Pair(newAccess, newRefresh)
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return null
    }
}
