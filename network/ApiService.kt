package com.example.messenger.network

import com.example.messenger.models.Chat
import com.example.messenger.models.Message
import com.example.messenger.models.Page
import com.example.messenger.models.User
import okhttp3.MultipartBody
import retrofit2.Call
import retrofit2.http.*
import java.util.UUID

data class LoginResponse(val access: String, val refresh: String, val user: User)
data class RegisterRequest(val username: String, val password: String)
data class TokenResponse(val access: String, val refresh: String? = null)
data class UserProfile(val user: User, val avatar: String?, val bio: String?)
data class UploadResponse(val url: String)
data class CreateMessageRequest(val chat_id: UUID, val text: String, val media_url: String? = null, val reply_to: UUID? = null, val is_forwarded: Boolean = false)
data class ReactionRequest(val emoji: String)
data class PinResponse(val pinned: Boolean)
data class ForwardRequest(val message_id: UUID, val chat_id: UUID)
data class SearchResponse(val results: List<Message>)

interface ApiService {
    @POST("register/")
    fun register(@Body request: RegisterRequest): Call<User>

    @POST("login/")
    fun login(@Body credentials: Map<String, String>): Call<LoginResponse>

    @POST("token/refresh/")
    fun refreshToken(@Body refreshRequest: Map<String, String>): Call<TokenResponse>

    @GET("profile/")
    fun getProfile(@Header("Authorization") auth: String): Call<UserProfile>

    @PUT("profile/")
    fun updateProfile(@Header("Authorization") auth: String, @Body profile: UserProfile): Call<UserProfile>

    @GET("users/search/")
    fun searchUsers(@Header("Authorization") auth: String, @Query("q") query: String): Call<List<User>>

    @GET("chats/")
    fun getChats(@Header("Authorization") auth: String): Call<List<Chat>>

    @POST("chats/")
    fun createChat(@Header("Authorization") auth: String, @Body chat: Chat): Call<Chat>

    @GET("chats/{chatId}/messages/")
    fun getMessages(@Header("Authorization") auth: String, @Path("chatId") chatId: UUID): Call<Page<Message>>

    @POST("upload/")
    @Multipart
    fun uploadFile(@Header("Authorization") auth: String, @Part file: MultipartBody.Part): Call<UploadResponse>

    @POST("messages/create/")
    fun createMessage(@Header("Authorization") auth: String, @Body message: CreateMessageRequest): Call<Message>

    @POST("messages/{messageId}/react/")
    fun react(@Header("Authorization") auth: String, @Path("messageId") messageId: UUID, @Body reaction: ReactionRequest): Call<Reaction>

    @POST("messages/{messageId}/pin/")
    fun pin(@Header("Authorization") auth: String, @Path("messageId") messageId: UUID): Call<PinResponse>

    @POST("messages/forward/")
    fun forward(@Header("Authorization") auth: String, @Body forward: ForwardRequest): Call<Message>

    @GET("messages/search/")
    fun searchMessages(@Header("Authorization") auth: String, @Query("q") query: String): Call<SearchResponse>
}
