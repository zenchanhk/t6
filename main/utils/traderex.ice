module TraderEx {

	interface DataReceiver {
		void onData(string data);
		void onError(string error);
		void onStatus(string status);
	};

	interface Server {
		bool register(string clientId, DataReceiver* receiver);
		["amd"] string execute(string command);
	};
}