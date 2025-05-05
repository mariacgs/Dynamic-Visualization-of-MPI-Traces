#include "TraceManager.h"
#include <string.h> 

int mock_received_msgs = 0;
int areReceivedMsg() {
    return (mock_received_msgs++ < 5);  // Returns true 5 times, then false
}
int main(int argc, char * const argv[])
{
    /* Simulator clock
    */
    int sim_clock=0;
    /* Configure the simulator
    sim_conﬁg();*/

    /* TraceLIB configuration struct
    */
    conf_t my_conf;
    my_conf.simNodes = 4;
    my_conf.number_of_traces = 1;
    my_conf.mapping_mode = 0;
    strncpy(my_conf.filename, "data/output_trace.vef", sizeof(my_conf.filename) - 1);
    my_conf.filename[sizeof(my_conf.filename) - 1] = '\0';  
    my_conf.use_simulator_clock_instead_of_factorTime = 0;

    /* Set the fields of my_conf and
    initialize TraceLIB
    */
    init_MultipleTraceManager(&my_conf);
    /* Start the simulation. The
    simulation finishes when the
    TraceLIB completes the trace
    execution
    */
    while (!isTraceComplete() && sim_clock < 100)
    {
        /* TraceLIB Message struct
        */
        msg_t msg;
        /* Does TraceLIB have messages to
        inject at current cycle?
        */
        while (areMsgstoGet())
        {
            /* Get the message and program
            the generation event
            */
            getMsgTrace(&msg);
           /* putEvent(GENERATION_EVENT, sim_clock,
            msg); */
        }
        /* Process the events programmed
        for the current cycle

        processEvents(sim_clock);
        */
        
        /* Check if there are received
        messages after the event
        processing
        */
       while (areReceivedMsg())
       {
        msg_t msg = {
            .dst = 0,  // Default values
            .id = mock_received_msgs
        };
          //  msg_t msg;
            /* Get the received message and
            report to TraceLIB
            */
            //getReceivedMessage(&msg);
            ReceiveTraceMsg(msg.dst, msg.id);
        }
        /* Update the clocks
        */
        sim_clock++;
        clock_tictac();
    }
    /* The simulations finishes and the
    statistics are recorded.
    record_sim_stats();
    */
    
}