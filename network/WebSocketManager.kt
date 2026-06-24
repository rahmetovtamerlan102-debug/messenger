package com.example.messenger.network

import com.example.messenger.utils.Constants
import okhttp3.*
import okhttp3.logging.HttpLoggingInterceptor
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WebSocketManager(
    private val listener: WebSocketListener,
    private val token: String
) {
    private var webSocket: WebSocket? = null

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BODY })
        .build()

    fun connect(room: String) {
        val url = "${Constants.WS_URL}${room}/"
        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $token")
            .build()
        webSocket = client.newWebSocket(request, listener)
    }

    fun sendMessage(text: String, mediaUrl: String = "", replyTo: String? = null, forwarded: Boolean = false) {
        val json = JSONObject().apply {
            put("action", "message")
            put("message", text)
            if (mediaUrl.isNotEmpty()) put("media_url", mediaUrl)
            replyTo?.let { put("reply_to", it) }
            put("forwarded", forwarded)
        }
        webSocket?.send(json.toString())
    }

    fun sendReaction(messageId: String, emoji: String) {
        val json = JSONObject().apply {
            put("action", "reaction")
            put("message_id", messageId)
            put("emoji", emoji)
        }
        webSocket?.send(json.toString())
    }

    fun sendPin(messageId: String) {
        val json = JSONObject().apply {
            put("action", "pin")
            put("message_id", messageId)
        }
        webSocket?.send(json.toString())
    }

    fun sendDelete(messageId: String, forAll: Boolean = false) {
        val json = JSONObject().apply {
            put("action", "delete")
            put("message_id", messageId)
            put("for_all", forAll)
        }
        webSocket?.send(json.toString())
    }

    fun sendTyping() {
        webSocket?.send(JSONObject().apply { put("action", "typing") }.toString())
    }

    fun sendRead(messageIds: List<String>) {
        webSocket?.send(JSONObject().apply {
            put("action", "read")
            put("message_ids", messageIds)
        }.toString())
    }

    fun disconnect() {
        webSocket?.close(1000, null)
        webSocket = null
    }
}
